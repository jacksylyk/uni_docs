from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_document, name='upload_document'),
    # path('', views.document_list, name='document_list'),
    # path('document/<int:doc_id>/', views.document_detail, name='document_detail'),
    # path('document/<int:doc_id>/version/<int:version_id>/', views.document_version_detail, name='document_version_detail'),
]
