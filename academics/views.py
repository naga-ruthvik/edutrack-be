from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.permissions import IsAuthenticated

from .models import Department
from .serializers import CreateDepartmentSerializer, DepartmentSerializer
from authentication.permissions import IsInstitutionAdmin


class CreateDepartmentAPIView(CreateAPIView):
    """
    Creates a Department in specific institution
    """

    queryset = Department.objects.all()
    serializer_class = CreateDepartmentSerializer
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]


class DepartmentListAPIView(ListAPIView):
    """
    Returns a list of all departments in the institution.
    """

    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]

    def get_queryset(self):
        return Department.objects.all()
