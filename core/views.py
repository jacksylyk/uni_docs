import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from documents.models import Document, Category, DocumentVersion, ApprovalDecision

User = get_user_model()

class IndexView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user

        # Документы, к которым у пользователя есть доступ
        accessible_documents = Document.objects.filter(
            accesses__user=user
        ).distinct()

        recent_documents = accessible_documents.order_by('-created_at')[:5]
        pending_documents = accessible_documents.filter(
            status='pending_review',
            approval_steps__order=F('current_step'),
            approval_steps__user=user
        ).distinct().select_related('category', 'created_by')
        print(pending_documents)
        categories = Category.objects.all()

        total_documents = accessible_documents.count()

        # Категории из доступных документов
        total_categories = Category.objects.filter(
            document__in=accessible_documents
        ).distinct().count()

        month_ago = timezone.now() - datetime.timedelta(days=30)
        monthly_changes = DocumentVersion.objects.filter(
            document__in=accessible_documents,
            created_at__gte=month_ago
        ).count()

        total_users = User.objects.count()

        recent_updates = DocumentVersion.objects.filter(
            document__in=accessible_documents
        ).select_related('document', 'uploaded_by').order_by('-created_at')[:5]

        context = {
            'recent_documents': recent_documents,
            'categories': categories,
            'total_documents': total_documents,
            'total_categories': total_categories,
            'monthly_changes': monthly_changes,
            'total_users': total_users,
            'recent_updates': recent_updates,
            'pending_documents': pending_documents
        }

        return render(request, 'index.html', context)


@login_required
def approve_document_step(request, pk):
    document = get_object_or_404(Document, pk=pk)
    try:
        step = document.approval_steps.all()[document.current_step]
    except IndexError:
        return HttpResponseForbidden("Неверный шаг согласования")

    if step.user != request.user:
        return HttpResponseForbidden("Вы не текущий согласующий.")

    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')

        ApprovalDecision.objects.create(
            step=step,
            decision='approved' if action == 'approve' else 'rejected',
            comment=comment
        )

        if action == 'approve':
            if document.current_step + 1 >= document.approval_steps.count():
                document.status = 'approved'
            else:
                document.current_step += 1
        else:
            document.status = 'rejected'

        document.save()
        messages.success(request, "Решение зафиксировано.")
        return redirect('document_detail', pk=pk)

    return render(request, 'documents/approve_step.html', {'document': document, 'step': step})