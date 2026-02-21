from django.db import transaction
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# Models
from authentication.models import User
from profiles.models import FacultyProfile, StudentProfile

# Permissions
from authentication.permissions import IsInstitutionAdmin, IsFaculty

# Serializers
from profiles.serializers import (
    CreateHODSerializer,
    HODListSerializer,
    StudentProfileSerializer,
)


# ---------------------------------------------------
# 1. HOD CREATE
# ---------------------------------------------------
class HODCreateView(GenericAPIView):
    """
    Creates a new HOD (Head of Department).
    Creates a User + FacultyProfile with is_hod=True in a single transaction.
    """

    serializer_class = CreateHODSerializer
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=data["email"],
                    username=data.get("username", data["email"]),
                    password=data["password"],
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    role=User.Role.FACULTY,
                )

                FacultyProfile.objects.create(
                    user=user,
                    employee_id=data.get("employee_id", f"HOD-{user.id}"),
                    department_id=data["department_id"],
                    designation=data.get("designation", "PROFESSOR"),
                    is_hod=True,
                )

                return Response({"message": "HOD Created", "id": user.id}, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=400)


# ---------------------------------------------------
# 2. HOD LIST
# ---------------------------------------------------
class HODListView(ListAPIView):
    """
    Lists all Heads of Department.
    """

    serializer_class = HODListSerializer
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]

    def get_queryset(self):
        return FacultyProfile.objects.filter(is_hod=True).select_related(
            "user", "department"
        )


# ---------------------------------------------------
# 3. FACULTY MENTEE LIST
# ---------------------------------------------------
class FacultyMenteeListView(ListAPIView):
    """
    Lists all students mentored by the currently logged-in faculty member.
    """

    permission_classes = [IsAuthenticated, IsFaculty]
    serializer_class = StudentProfileSerializer

    def get_queryset(self):
        return StudentProfile.objects.filter(
            mentor=self.request.user.faculty_profile
        ).select_related("user", "department")
