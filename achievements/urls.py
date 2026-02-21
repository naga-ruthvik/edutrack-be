from django.urls import path
from .views import (
    CertificateUploadView,
    certificate_list_view,
    certificate_verify_view,
    CertificateDetailView,
    total_score_view,
    student_achievements_view,
)

urlpatterns = [
    path("certificates/", certificate_list_view, name="certificate_list"),
    path(
        "certificates/upload/",
        CertificateUploadView.as_view(),
        name="certificate_upload",
    ),
    path(
        "certificates/<int:pk>/",
        CertificateDetailView.as_view(),
        name="certificate_detail",
    ),
    path(
        "certificates/<int:pk>/verify/",
        certificate_verify_view,
        name="certificate_verify",
    ),
    path("total-score/", total_score_view, name="total_score"),
    path(
        "student-achievements/", student_achievements_view, name="student_achievements"
    ),
]
