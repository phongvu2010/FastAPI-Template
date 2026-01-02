from django.urls import path
from . import views

urlpatterns = [
    path('documents/', views.DocumentUploadView.as_view(), name='document-upload'),
    path('documents/<uuid:id>/', views.DocumentDetailView.as_view(), name='document-detail'),
    path('documents/<uuid:id>/versions/<uuid:vid>/approve/', views.ApproveVersionView.as_view(), name='document-approve'),
    path('documents/<uuid:id>/reject/', views.RejectDocumentView.as_view(), name='document-reject'),
    path('documents/<uuid:id>/download/', views.DownloadApprovedFileView.as_view(), name='document-download'),
    path('documents/<uuid:id>/sign_internal/', views.SignInternalView.as_view(), name='document-sign-internal'),
    path('signatures/<uuid:id>/verify/', views.VerifySignatureView.as_view(), name='signature-verify'),

    path('documents/<uuid:id>/upload_signed_external/', views.UploadExternalSignedView.as_view(), name='document-upload-signed-external'),
]
