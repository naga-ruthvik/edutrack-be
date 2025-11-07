from django.urls import path
from .views import InstitutionStudentsListAPIView



urlpatterns=[
    path('institution-students', InstitutionStudentsListAPIView.as_view(), name="list_students"),
]