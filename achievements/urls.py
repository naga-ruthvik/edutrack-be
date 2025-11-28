from django.urls import path
from .views import CertificateUploadAPIView

urlpatterns=[
    path('upload-certificate',CertificateUploadAPIView.as_view(),name='certificate_upload'),
]