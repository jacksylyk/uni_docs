from django.contrib import messages
from django.utils import timezone

from users.models import Position
from .document_index import DocumentVersionDocument
from django.db.models import Q, F
from django_elasticsearch_dsl.search import Search
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth import get_user_model

from django.views import View
from django.views.generic import DetailView, ListView, TemplateView, FormView
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin

from .formsets import ApprovalStepFormSet
from .models import Document, DocumentVersion, Category, DocumentAccess, ApprovalDecision, ApprovalStep
from .forms import DocumentUploadForm, DocumentUpdateForm, DocumentAccessForm, AssignApproversForm
from .utils import extract_text_from_docx, get_word_diff, classify_document_with_openai, get_diff_description
import boto3
from django.views.decorators.http import require_GET

User = get_user_model()

@require_GET
def get_users_by_position(request):
    position_id = request.GET.get('position_id')
    if not position_id:
        return JsonResponse({'users': []})

    users = User.objects.filter(position_id=position_id).values('id', 'full_name', 'email')
    user_list = [
        {'id': u['id'], 'name': f"{u['full_name']} ({u['email']})"}
        for u in users
    ]
    return JsonResponse({'users': user_list})

def get_presigned_url(request, document_id, version_number):
    try:
        version = DocumentVersion.objects.get(document__id=document_id, version_number=version_number)
        file_key = version.file.name

        s3 = boto3.client('s3',
                          endpoint_url=settings.STORAGES['default']['OPTIONS']['endpoint_url'],
                          aws_access_key_id=settings.STORAGES['default']['OPTIONS']['access_key'],
                          aws_secret_access_key=settings.STORAGES['default']['OPTIONS']['secret_key'],
                          )

        presigned_url = s3.generate_presigned_url('get_object', Params={
            'Bucket': settings.STORAGES['default']['OPTIONS']['bucket_name'],
            'Key': file_key,
        }, ExpiresIn=300)
        return redirect(presigned_url)
    except DocumentVersion.DoesNotExist:
        return HttpResponseForbidden("Документ не найден")

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'documents/list.html'
    context_object_name = 'documents'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category')

        user = self.request.user
        queryset = queryset.filter(Q(created_by=user) | Q(accesses__user=user)).distinct()

        category_id = self.request.GET.get('category')
        status = self.request.GET.get('status')
        search = self.request.GET.get('search')

        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(title__icontains=search)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['selected_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context

class DocumentDetailView(LoginRequiredMixin, DetailView, FormView):
    model = Document
    template_name = 'documents/detail.html'
    context_object_name = 'document'
    form_class = DocumentAccessForm

    def get_queryset(self):
        user = self.request.user
        return Document.objects.filter(Q(created_by=user) | Q(accesses__user=user)).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.get_object()
        user = self.request.user

        can_edit = DocumentAccess.objects.filter(
            document=document,
            user=user,
            can_edit=True
        ).exists() or document.created_by == user or user.is_superuser

        approval_step = document.approval_steps.filter(user=user).first()
        if approval_step:
            is_approver = document.status == 'pending_review' and approval_step.order == document.current_step and approval_step.user == user
        else:
            is_approver = False
        context.update({
            'versions': document.versions.all(),
            'last_version': document.versions.order_by('-version_number').first(),
            'accesses': DocumentAccess.objects.filter(document=document).select_related('user'),
            'form': self.get_form(),
            'can_edit': can_edit,
            'is_approver': is_approver
        })
        return context

    def form_valid(self, form):
        document = self.get_object()
        access = form.save(commit=False)
        access.document = document
        access.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('document_detail', kwargs={'pk': self.get_object().pk})


class DocumentUploadView(LoginRequiredMixin, FormView):
    form_class = DocumentUploadForm
    template_name = 'documents/upload.html'
    success_url = reverse_lazy('document_list')

    def form_valid(self, form):
        doc_title = form.cleaned_data['document']
        file = form.cleaned_data['file']
        comment = form.cleaned_data['comment']

        content = extract_text_from_docx(file)

        categories = Category.objects.all()

        predicted_category_name = classify_document_with_openai(content, categories)

        predicted_category = Category.objects.filter(name=predicted_category_name).first()
        if not predicted_category:
            predicted_category = Category.objects.create(name=predicted_category_name)

        document, created = Document.objects.get_or_create(
            title=doc_title,
            defaults={'created_by': self.request.user, 'category': predicted_category}
        )

        latest_version = document.versions.first()
        next_version = latest_version.version_number + 1 if latest_version else 1

        document_version = DocumentVersion.objects.create(
            document=document,
            version_number=next_version,
            file=file,
            uploaded_by=self.request.user,
            comment=comment,
            content_text=content
        )

        DocumentAccess.objects.get_or_create(document=document, user=self.request.user, can_edit=True)

        return redirect('document_detail', pk=document.pk)

class CompareVersionsView(LoginRequiredMixin, View):
    template_name = 'documents/compare.html'

    def get(self, request, document_id, version_number):
        document = get_object_or_404(Document, pk=document_id)
        current = get_object_or_404(DocumentVersion, document=document, version_number=version_number)
        previous = document.versions.filter(version_number__lt=version_number).first()

        if not previous:
            return render(request, self.template_name, {
                'document': document,
                'message': "Это первая версия, сравнивать не с чем."
            })

        diff_lines = []

        prev_lines = previous.content_text.splitlines()
        curr_lines = current.content_text.splitlines()

        for i in range(max(len(prev_lines), len(curr_lines))):
            a = prev_lines[i] if i < len(prev_lines) else ''
            b = curr_lines[i] if i < len(curr_lines) else ''
            diff_lines.append(get_word_diff(a, b))

        return render(request, self.template_name, {
            'document': document,
            'diff': diff_lines
        })

class DocumentUpdateView(LoginRequiredMixin, FormView):
    form_class = DocumentUpdateForm
    template_name = 'documents/update.html'

    def get_object(self):
        return get_object_or_404(Document, pk=self.kwargs['pk'])

    def dispatch(self, request, *args, **kwargs):
        document = self.get_object()
        user = request.user

        has_access = (
                document.created_by == user or
                DocumentAccess.objects.filter(document=document, user=user, can_edit=True).exists()
        )

        if not has_access:
            messages.error(request, "<UNK> <UNK> <UNK>")
            return redirect('index')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document'] = self.get_object()
        return context

    def form_valid(self, form):
        document = self.get_object()
        document.save()

        new_file = self.request.FILES.get('file')
        if new_file:
            latest_version = document.versions.first()
            next_version = latest_version.version_number + 1 if latest_version else 1
            new_content = extract_text_from_docx(new_file)

            ai_description = ""
            if latest_version and latest_version.content_text:
                ai_description = get_diff_description(latest_version.content_text, new_content)

            DocumentVersion.objects.create(
                document=document,
                version_number=next_version,
                file=new_file,
                uploaded_by=self.request.user,
                comment=form.cleaned_data.get('comment', ''),
                content_text=new_content,
                ai_description=ai_description
            )

        return redirect('document_detail', pk=document.pk)

class DocumentSearchView(LoginRequiredMixin, TemplateView):
    template_name = 'documents/search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q')
        results = []

        if query:
            # Выполнить поиск в Elasticsearch
            search = DocumentVersionDocument.search().query(
                "multi_match",
                query=query,
                fields=['content_text', 'title', 'author']
            )

            raw_results = search.execute()

            # Получить document_id из результатов
            matched_doc_ids = {hit.document_id for hit in raw_results if hit.document_id}

            # Получить ID документов, доступных пользователю
            accessible_doc_ids = set(
                DocumentAccess.objects.filter(user=self.request.user)
                .values_list('document_id', flat=True)
            )

            # Оставить только те, что пользователь может видеть
            filtered_results = [hit for hit in raw_results if hit.document_id in accessible_doc_ids]

            results = filtered_results

        context['query'] = query
        context['results'] = results
        return context


class RevokeAccessView(LoginRequiredMixin, View):
    def post(self, request, document_id, access_id):
        document = get_object_or_404(Document, id=document_id)

        if document.created_by != request.user:
            messages.error(request, "У вас нет прав на удаление доступа.")
            return redirect('document_detail', pk=document_id)

        access = get_object_or_404(DocumentAccess, id=access_id, document=document)
        access.delete()
        messages.success(request, f"Доступ пользователя {access.user} отозван.")
        return redirect('document_detail', pk=document_id)


class AssignDynamicApproversView(View):
    template_name = 'documents/assign_dynamic_approvers.html'

    def get(self, request, pk):
        document = get_object_or_404(Document, pk=pk)

        teacher_position = Position.objects.get(name='Преподаватель')

        # Устанавливаем initial, если позиция найдена
        initial = [{'position': teacher_position.id}] if teacher_position else [{}]

        formset = ApprovalStepFormSet(initial=initial)

        return render(request, self.template_name, {
            'formset': formset,
            'document': document
        })

    def post(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        formset = ApprovalStepFormSet(request.POST)

        if formset.is_valid():
            # Удалим старые шаги
            document.approval_steps.all().delete()

            for index, form in enumerate(formset):
                role = form.cleaned_data['position']
                user = form.cleaned_data['user']

                ApprovalStep.objects.create(
                    document=document,
                    position=role,
                    user=user,
                    order=index
                )
                DocumentAccess.objects.create(
                    document=document,
                    user=user
                )

            document.status = 'pending_review'
            document.sent_for_review_at = timezone.now()
            document.current_step = 0
            document.save()

            return redirect('document_detail', pk=document.pk)

        return render(request, self.template_name, {'formset': formset, 'document': document})

