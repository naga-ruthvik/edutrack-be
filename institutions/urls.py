from django.urls import path
from .views import InstitutionStudentsAPIView
urlpatterns=[
    path('institutions-students', InstitutionStudentsAPIView.as_view(), name="list_institution_students")
]