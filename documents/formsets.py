from django.forms import formset_factory

from documents.forms import ApprovalStepForm

ApprovalStepFormSet = formset_factory(ApprovalStepForm, extra=0, min_num=1, validate_min=True)
