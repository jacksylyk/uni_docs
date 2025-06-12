from django.urls import path

from core.views import approve_document_step
from .views import *

urlpatterns = [
    path('', DocumentListView.as_view(), name='document_list'),
    path('upload/', DocumentUploadView.as_view(), name='upload_document'),
    path('<int:pk>/', DocumentDetailView.as_view(), name='document_detail'),
    path('<int:document_id>/compare/<int:version_number>/', CompareVersionsView.as_view(), name='compare_versions'),
    path('<int:pk>/edit/', DocumentUpdateView.as_view(), name='update_document'),
    path('<int:document_id>/v<int:version_number>/url/', get_presigned_url, name='get_presigned_url'),
    path('search/', DocumentSearchView.as_view(), name='document_search'),
    path('<int:document_id>/access/<int:access_id>/revoke/', RevokeAccessView.as_view(), name='revoke_access'),
    path('<int:pk>/assign/', AssignDynamicApproversView.as_view(), name='assign_approvers'),
    path('<int:pk>/approve_document_step/', approve_document_step, name="approve_document_step"),


    path('ajax/get-users-by-position/', get_users_by_position, name='get_users_by_position'),
]
