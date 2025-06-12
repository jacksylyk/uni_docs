from django_elasticsearch_dsl.signals import RealTimeSignalProcessor
from django_elasticsearch_dsl.registries import registry
from elasticsearch_dsl import connections 
from django.db.models.signals import post_save, pre_delete
from documents.models import DocumentVersion
from django.dispatch import receiver

class CustomSignalProcessor(RealTimeSignalProcessor):
    pass

registry.signal_processor = CustomSignalProcessor(connections)

@receiver(post_save, sender=DocumentVersion)
def update_document_version_in_elasticsearch(sender, instance, **kwargs):
    registry.update(instance)
