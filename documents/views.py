import difflib
from django.utils.html import escape

from django.views import View
from django.views.generic import DetailView, ListView, FormView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Document, DocumentVersion
from .forms import DocumentUploadForm, DocumentUpdateForm
from .utils import extract_text_from_docx, get_word_diff

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'documents/list.html'
    context_object_name = 'documents'


class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = Document
    template_name = 'documents/detail.html'
    context_object_name = 'document'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['versions'] = self.object.versions.all()
        return context


class DocumentUploadView(LoginRequiredMixin, FormView):
    form_class = DocumentUploadForm
    template_name = 'documents/upload.html'
    success_url = reverse_lazy('document_list')

    def form_valid(self, form):
        doc_title = form.cleaned_data['document']
        file = form.cleaned_data['file']
        comment = form.cleaned_data['comment']

        document, created = Document.objects.get_or_create(
            title=doc_title,
            defaults={'created_by': self.request.user}
        )
        latest_version = document.versions.first()
        next_version = latest_version.version_number + 1 if latest_version else 1

        content = extract_text_from_docx(file)

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
        document.title = form.cleaned_data['title']
        document.comment = form.cleaned_data['comment']
        document.save()

        # Если был загружен новый файл, создаем новую версию
        new_file = self.request.FILES.get('file')
        if new_file:
            latest_version = document.versions.first()
            next_version = latest_version.version_number + 1 if latest_version else 1
            content = extract_text_from_docx(new_file)

            DocumentVersion.objects.create(
                document=document,
                version_number=next_version,
                file=new_file,
                uploaded_by=self.request.user,
                comment=form.cleaned_data.get('comment', ''),
                content_text=content
            )

        return redirect('document_detail', pk=document.pk)