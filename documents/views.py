from .document_index import DocumentVersionDocument
from django.db.models import Q
from django_elasticsearch_dsl.search import Search
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.html import escape

from django.views import View
from django.views.generic import DetailView, ListView, TemplateView, FormView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Document, DocumentVersion, Category
from .forms import DocumentUploadForm, DocumentUpdateForm
from .utils import extract_text_from_docx, get_word_diff, classify_document_with_openai, get_diff_description
import boto3

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

class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = Document
    template_name = 'documents/detail.html'
    context_object_name = 'document'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['versions'] = self.object.versions.all()
        context['last_version'] = self.object.versions.order_by('-version_number').first()
        return context


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

        DocumentVersion.objects.create(
            document=document,
            version_number=next_version,
            file=file,
            uploaded_by=self.request.user,
            comment=comment,
            content_text=content
        )

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

    def get_object(self, **kwargs):
        return get_object_or_404(Document, pk=self.kwargs['pk'])

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
            search = DocumentVersionDocument.search().query(
                "multi_match",
                query=query,
                fields=['content_text', 'document_title', 'author']
            )
            results = search.execute()

        context['query'] = query
        context['results'] = results
        return context