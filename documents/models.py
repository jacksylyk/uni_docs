from django.db import models
from django.conf import settings


class Document(models.Model):
    DOCUMENT_TYPES = [
        ('order', 'Приказ'),
        ('regulation', 'Положение'),
        ('instruction', 'Инструкция'),
        ('other', 'Другое'),
    ]

    title = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES, default='other')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_doc_type_display()})"


class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, related_name='versions', on_delete=models.CASCADE)
    version_number = models.PositiveIntegerField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('document', 'version_number')
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.document.title} - Версия {self.version_number}"
