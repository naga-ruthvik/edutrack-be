from django.urls import path
from .views import InstitutionRegisterView

urlpatterns=[
    # path('institution-students', InstitutionStudentsListAPIView.as_view(), name="list_students"),
    path('institution-register',InstitutionRegisterView.as_view(),name='institution_register'),
]