from django.urls import path
from .views import RegisterCollegeView, ListCollegesView

urlpatterns = [
    path('register-college/', RegisterCollegeView.as_view(), name='register_college'),
    path('institutions/', ListCollegesView.as_view(), name='list_colleges'),
]