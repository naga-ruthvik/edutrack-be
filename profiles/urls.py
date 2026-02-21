from django.urls import path
from profiles.views import (
    # Student views
    StudentListView,
    StudentProfileListView,
    StudentDetailView,
    StudentCreateView,
    student_total_view,
    student_list_all_view,
    student_data_view,
    # Faculty views
    HODCreateView,
    HODListView,
    FacultyMenteeListView,
    # Bulk upload
    BulkProfileUploadView,
)

urlpatterns = [
    # students
    path("students/", StudentListView.as_view(), name="student_list"),
    path("students/<int:pk>/", StudentDetailView.as_view(), name="student_detail"),
    path("students/create/", StudentCreateView.as_view(), name="student_create"),
    path("students/all/", student_list_all_view, name="student_list_all"),
    path(
        "students/profile/",
        StudentProfileListView.as_view(),
        name="student_profile_list",
    ),
    path("students/data/", student_data_view, name="student_data"),
    path("students/total/", student_total_view, name="student_total"),
    # faculty
    path(
        "faculty/mentees/", FacultyMenteeListView.as_view(), name="faculty_mentee_list"
    ),
    # HODs
    path("hods/", HODListView.as_view(), name="hod_list"),
    path("hods/create/", HODCreateView.as_view(), name="hod_create"),
    # Bulk Upload
    path("bulk-upload/", BulkProfileUploadView.as_view(), name="profile_bulk_upload"),
]
