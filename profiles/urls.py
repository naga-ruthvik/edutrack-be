from django.urls import path
from profiles.views import (
    # Student views
    StudentListCreateView,
    StudentDetailView,
    student_total_view,
    student_data_view,
    # Faculty views
    HODListCreateView,
    FacultyMenteeListView,
    # Bulk upload
    BulkProfileUploadView,
)

urlpatterns = [
    # students
    path("students/", StudentListCreateView.as_view(), name="student_list_create"),
    path("students/<int:pk>/", StudentDetailView.as_view(), name="student_detail"),
    path("students/data/", student_data_view, name="student_data"),
    path("students/total/", student_total_view, name="student_total"),
    # faculty
    path(
        "faculty/mentees/", FacultyMenteeListView.as_view(), name="faculty_mentee_list"
    ),
    # HODs
    path("hods/", HODListCreateView.as_view(), name="hod_list"),
    # Bulk Upload
    path("bulk-upload/", BulkProfileUploadView.as_view(), name="profile_bulk_upload"),
]
