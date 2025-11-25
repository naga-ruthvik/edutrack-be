from django.urls import path
from .views import InstitutionStudentsAPIView,CreateBulkProfilesView,DepartmentProfileCreateAPIView, CreateDepartmentAPIView, CreateHOD_APIView, ListHOD_APIView
urlpatterns=[
    path('institutions-students', InstitutionStudentsAPIView.as_view(), name="list_institution_students"),
    path('create-bulk-profiles',CreateBulkProfilesView.as_view(),name='create_bulk_profiles'),
    path('create-dept-profile', DepartmentProfileCreateAPIView.as_view(), name='create_dept_profile'),
    path('create-department',CreateDepartmentAPIView.as_view(), name="create_department"),
    path('create-hod',CreateHOD_APIView.as_view(),name="create_hod"),
    path('list-hods',ListHOD_APIView.as_view(),name='list-hods')
]