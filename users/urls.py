from django.urls import path
from .views import InstitutionRegisterView

urlpatterns=[
    path('institution-register',InstitutionRegisterView.as_view(),name='institution_register'),
]