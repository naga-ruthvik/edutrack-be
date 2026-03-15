from django.urls import path

from .views import DepartmentListCreateView

urlpatterns = [
    path("departments/", DepartmentListCreateView.as_view(), name="department_list"),
]
