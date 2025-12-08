from django.urls import path
from .views import CertificateUploadAPIView, list_certificates, verify_certificates, CertificateRetrieveAPIView

urlpatterns=[
    path('upload-certificate',CertificateUploadAPIView.as_view(),name='certificate_upload'),
    path('certificates',list_certificates,name='list_certificates'),
    path('verify-certificate/<int:pk>', verify_certificates, name='verify_certificate'),
    path('certificates/<int:pk>/',CertificateRetrieveAPIView.as_view(),name='certificate_retrieve'),
]