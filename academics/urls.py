from django.urls import path

from .views import CreateDepartmentAPIView, DepartmentListAPIView

urlpatterns = [
    path("departments/", DepartmentListAPIView.as_view(), name="department_list"),
    path(
        "departments/create/",
        CreateDepartmentAPIView.as_view(),
        name="department_create",
    ),  # fmt: skip
]
