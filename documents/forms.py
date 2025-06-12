from django import forms

from documents.models import Document, DocumentVersion


class DocumentUploadForm(forms.Form):
    document = forms.CharField(label="Название документа")
    file = forms.FileField()
    comment = forms.CharField(widget=forms.Textarea, required=False)

class DocumentUpdateForm(forms.ModelForm):
    class Meta:
        model = DocumentVersion
        fields = ['file']