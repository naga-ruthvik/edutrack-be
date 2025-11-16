from django.urls import path
from .views import InstitutionStudentsAPIView,create_profiles
urlpatterns=[
    path('institutions-students', InstitutionStudentsAPIView.as_view(), name="list_institution_students"),
    path('create-profiles',create_profiles,name='create_inst_profiles'),
]