import datetime

from django.shortcuts import render
from django.views import View
from django.utils import timezone
from documents.models import Document, DocumentVersion, Category
from users.models import User


class IndexView(View):
    def get(self, request):
        recent_documents = Document.objects.all().order_by('-created_at')[:5]

        categories = Category.objects.all()

        total_documents = Document.objects.count()
        total_categories = Category.objects.count()

        month_ago = timezone.now() - datetime.timedelta(days=30)
        monthly_changes = DocumentVersion.objects.filter(created_at__gte=month_ago).count()

        total_users = User.objects.count()

        recent_updates = DocumentVersion.objects.select_related('document', 'uploaded_by').order_by('-created_at')[:5]

        context = {
            'recent_documents': recent_documents,
            'categories': categories,
            'total_documents': total_documents,
            'total_categories': total_categories,
            'monthly_changes': monthly_changes,
            'total_users': total_users,
            'recent_updates': recent_updates,
        }

        return render(request, 'index.html', context)