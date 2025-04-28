from django.urls import path
from .views import *
urlpatterns = [
    path('', DocumentListView.as_view(), name='document_list'),
    path('upload/', DocumentUploadView.as_view(), name='upload_document'),
    path('<int:pk>/', DocumentDetailView.as_view(), name='document_detail'),
    path('<int:document_id>/compare/<int:version_number>/', CompareVersionsView.as_view(), name='compare_versions'),
    path('<int:pk>/edit/', DocumentUpdateView.as_view(), name='document_edit'),
]
