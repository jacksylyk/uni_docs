from django.shortcuts import render, redirect
from .models import Document, DocumentVersion
from .utils import extract_text_from_docx
from .forms import DocumentUploadForm  # создадим форму чуть позже
from django.contrib.auth.decorators import login_required

@login_required
def upload_document(request):
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.cleaned_data['document']
            file = form.cleaned_data['file']
            comment = form.cleaned_data['comment']

            # если документа ещё нет — создаём
            document, created = Document.objects.get_or_create(
                title=doc,
                defaults={'created_by': request.user}
            )

            # определим номер версии
            latest_version = document.versions.first()
            next_version = latest_version.version_number + 1 if latest_version else 1

            # извлечение текста
            text = extract_text_from_docx(file)

            # создаём версию
            version = DocumentVersion.objects.create(
                document=document,
                version_number=next_version,
                file=file,
                uploaded_by=request.user,
                comment=comment,
                content_text=text,
            )
            return redirect('document_detail', pk=document.pk)
    else:
        form = DocumentUploadForm()
    return render(request, 'documents/upload.html', {'form': form})
