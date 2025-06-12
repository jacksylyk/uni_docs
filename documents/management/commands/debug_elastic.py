# Run this in Django shell: python manage.py shell

from documents.models import DocumentVersion  # Replace with your app name
from documents.document_index import DocumentVersionDocument  # Replace with your app name
from elasticsearch.helpers import BulkIndexError
import json
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Debug Elasticsearch indexing for DocumentVersion"

    def handle(self, *args, **options):
        # Your actual code here
        print("Running debug_elastic command...")
        # Get the single DocumentVersion object
        version = DocumentVersion.objects.first()
        print(f"Processing DocumentVersion ID: {version.id}")

        # Check all the data
        print("\n=== Raw Data ===")
        print(f"version_number: {getattr(version, 'version_number', 'MISSING')}")
        print(f"document: {version.document if hasattr(version, 'document') else 'MISSING'}")
        if hasattr(version, 'document') and version.document:
            print(f"  document.id: {version.document.id}")
            print(f"  document.title: {repr(version.document.title)}")

        print(f"uploaded_by: {version.uploaded_by if hasattr(version, 'uploaded_by') else 'MISSING'}")
        if hasattr(version, 'uploaded_by') and version.uploaded_by:
            print(f"  uploaded_by.email: {repr(version.uploaded_by.email)}")

        print(f"content_text: {type(getattr(version, 'content_text', None))} - {len(version.content_text) if version.content_text else 0} chars")
        print(f"comment: {type(getattr(version, 'comment', None))} - {len(version.comment) if version.comment else 0} chars")
        print(f"ai_description: {type(getattr(version, 'ai_description', None))} - {len(version.ai_description) if version.ai_description else 0} chars")
        print(f"uploaded_at: {version.uploaded_at} ({type(version.uploaded_at)})")

        # Try to prepare the document
        print("\n=== Document Preparation ===")
        doc = DocumentVersionDocument()
        try:
            prepared_data = doc.prepare(version)
            print("✅ Document preparation successful")
            print("Prepared data:")
            for key, value in prepared_data.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  {key}: {type(value)} - {len(value)} chars - {repr(value[:50])}...")
                else:
                    print(f"  {key}: {repr(value)}")
        except Exception as e:
            print(f"❌ Document preparation failed: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()

        # Try to index the single document
        print("\n=== Single Document Indexing ===")
        try:
            doc.update(version)
            print("✅ Single document indexing successful")
        except BulkIndexError as e:
            print(f"❌ BulkIndexError occurred")
            print(f"Error message: {e}")
            if hasattr(e, 'errors'):
                print("Detailed errors:")
                for i, error in enumerate(e.errors):
                    print(f"  Error {i+1}: {json.dumps(error, indent=4) if isinstance(error, dict) else error}")
        except Exception as e:
            print(f"❌ Other error: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()