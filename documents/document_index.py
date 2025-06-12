from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from .models import DocumentVersion

@registry.register_document
class DocumentVersionDocument(Document):
    title = fields.TextField(attr='document.title')
    content_text = fields.TextField()
    comment = fields.TextField()
    ai_description = fields.TextField()
    author = fields.TextField(attr='uploaded_by.email')
    uploaded_at = fields.DateField()
    document_id = fields.IntegerField(attr='document.id')

    def prepare_content_text(self, instance):
        return instance.content_text or ""

    def prepare_comment(self, instance):
        return instance.comment or ""

    def prepare_ai_description(self, instance):
        return instance.ai_description or ""

    def prepare_title(self, instance):
        # Handle case where document might be None
        return instance.document.title if instance.document else ""

    def prepare_author(self, instance):
        # Handle case where uploaded_by might be None
        return instance.uploaded_by.email if instance.uploaded_by else ""

    def prepare_document_id(self, instance):
        # Handle case where document might be None
        return instance.document.id if instance.document else None

    def prepare_uploaded_at(self, instance):
        # Convert datetime to ISO string format for Elasticsearch
        if instance.uploaded_at:
            return instance.uploaded_at.isoformat()
        return None

    class Index:
        name = 'document_versions'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
            'index.max_result_window': 50000,
            'index.mapping.total_fields.limit': 2000
        }

    class Django:
        model = DocumentVersion
        fields = [
            'version_number',
        ]