from django_elasticsearch_dsl import Document, Index, fields
from django_elasticsearch_dsl.registries import registry
from .models import DocumentVersion

document_index = Index('document_versions')

document_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@registry.register_document
class DocumentVersionDocument(Document):
    title = fields.TextField(attr='document.title')
    content_text = fields.TextField()
    comment = fields.TextField()
    ai_description = fields.TextField()
    author = fields.TextField(attr='uploaded_by.email')
    uploaded_at = fields.DateField()
    document_id = fields.IntegerField(attr='document.id')

    class Index:
        name = 'document_versions'

    class Django:
        model = DocumentVersion
        fields = [
            'version_number',
        ]
