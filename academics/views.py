from rest_framework.generics import ListAPIView, CreateAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated

from .models import Department
from .serializers import DepartmentListSerializer, DepartmentCreateSerializer
from authentication.permissions import IsInstitutionAdmin


class DepartmentListCreateView(ListCreateAPIView):
    """
    Returns a list of all departments in the institution.
    """

    queryset = Department.objects.all()
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]

    def get_serializer_class(self):
        if self.request.method in ["POST"]:
            return DepartmentCreateSerializer
        return DepartmentListSerializer
