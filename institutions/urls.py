from django.urls import path
from .views import InstitutionStudentsAPIView,CreateProfilesView
urlpatterns=[
    path('institutions-students', InstitutionStudentsAPIView.as_view(), name="list_institution_students"),
    path('create-profiles',CreateProfilesView.as_view(),name='create_inst_profiles'),
]