from django.urls import path
from .views import (
    InstitutionStudentsAPIView,
    CreateBulkProfilesView,
    CreateDepartmentAPIView,
    CreateHOD_APIView,
    ListHOD_APIView,
    DepartmentListAPIView,
    total_students_view,
    total_score_view
    # Removed DepartmentProfileCreateAPIView (Use Djoser or Bulk instead)
)

urlpatterns = [
    # List all students in this college
    path('academics-students/', InstitutionStudentsAPIView.as_view(), name="list_institution_students"),
    
    # Upload Excel file to create users
    path('create-bulk-profiles/', CreateBulkProfilesView.as_view(), name='create_bulk_profiles'),
    
    # Create a Department (e.g. CSE)
    path('create-department/', CreateDepartmentAPIView.as_view(), name="create_department"),
    
    # Create HOD
    path('create-hod/', CreateHOD_APIView.as_view(), name="create_hod"),
    
    # List HODs
    path('list-hods/', ListHOD_APIView.as_view(), name='list-hods'),
    path('departments/',DepartmentListAPIView.as_view(),name="department-list"),
    path('total-students/',total_students_view,name="total_students"),
    path('total-score/',total_score_view,name="total_score")
]