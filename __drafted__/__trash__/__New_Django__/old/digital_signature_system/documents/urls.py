from django.urls import path
from .views import DocumentUploadView, DocumentReviewView, DocumentSignView

urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document_upload'),
    path('<int:document_id>/review/', DocumentReviewView.as_view(), name='document_review'),
    path('<int:document_id>/sign/', DocumentSignView.as_view(), name='document_sign'), # Thêm URL mới
]
