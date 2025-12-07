from django.urls import path
from .views import CertificateUploadAPIView,list_certificates

urlpatterns=[
    path('upload-certificate',CertificateUploadAPIView.as_view(),name='certificate_upload'),
    path('certificates',list_certificates,name='list_certificates'),
]