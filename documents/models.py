from django.db import models
from django.conf import settings
from django.utils import timezone

from users.models import Position


class Document(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('pending_review', 'На согласовании'),
        ('approved', 'Согласовано'),
        ('rejected', 'Отклонено'),
    ]

    title = models.CharField(max_length=255)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    category = models.ForeignKey("Category", on_delete=models.SET_NULL, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    current_step = models.PositiveIntegerField(default=0)
    sent_for_review_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

class ApprovalStep(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='approval_steps')
    position = models.ForeignKey(Position, on_delete=models.CASCADE, verbose_name='Должность')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Пользователь')
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.position.name} — {self.user}"

class ApprovalDecision(models.Model):
    step = models.OneToOneField(ApprovalStep, on_delete=models.CASCADE, related_name='decision')
    decision = models.CharField(max_length=10, choices=[('approved', 'Согласовано'), ('rejected', 'Отклонено')])
    comment = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.step} - {self.get_decision_display()}"

def document_version_upload_to(instance, filename):
    return f"documents/{instance.document.id}/v{instance.version_number}/{filename}"

class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to=document_version_upload_to)
    uploaded_at = models.DateTimeField(default=timezone.now)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField(blank=True, null=True)
    ai_description = models.TextField(blank=True, null=True)
    content_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('document', 'version_number')
        ordering = ['-version_number']

    def update(self, instance, *args, **kwargs):
        if not instance.content_text:
            instance.content_text = ""
        if not instance.comment:
            instance.comment = ""
        return super().update(instance, *args, **kwargs)

    def __str__(self):
        return f"{self.document.title} v{self.version_number}"


class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class DocumentAccess(models.Model):
    document = models.ForeignKey('Document', on_delete=models.CASCADE, related_name='accesses')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    can_edit = models.BooleanField(default=False)

    class Meta:
        unique_together = ('document', 'user')