from django import forms

class DocumentUploadForm(forms.Form):
    document = forms.CharField(label="Название документа")
    file = forms.FileField()
    comment = forms.CharField(widget=forms.Textarea, required=False)
