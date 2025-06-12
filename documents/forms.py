from django import forms

from documents.models import Document, DocumentVersion, DocumentAccess, ApprovalStep
from django.contrib.auth import get_user_model

User = get_user_model()

class DocumentUploadForm(forms.Form):
    document = forms.CharField(label="Название документа")
    file = forms.FileField()
    comment = forms.CharField(widget=forms.Textarea, required=False)

class DocumentUpdateForm(forms.ModelForm):
    class Meta:
        model = DocumentVersion
        fields = ['file']


class DocumentAccessForm(forms.ModelForm):
    class Meta:
        model = DocumentAccess
        fields = ['user', 'can_edit']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:ring focus:ring-blue-200 p-2'
            }),
            'can_edit': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring focus:ring-blue-300'
            })
        }

class ApprovalStepForm(forms.ModelForm):
    class Meta:
        model = ApprovalStep
        fields = ['position', 'user']

class AssignApproversForm(forms.Form):
    teacher = forms.ModelChoiceField(queryset=User.objects.all(), label="Преподаватель")
    head = forms.ModelChoiceField(queryset=User.objects.all(), label="Заведующий")
    dean = forms.ModelChoiceField(queryset=User.objects.all(), label="Декан")