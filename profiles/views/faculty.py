from django.db import transaction
from rest_framework.generics import GenericAPIView, ListAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# Models
from authentication.models import User
from profiles.models import FacultyProfile, StudentProfile

# Permissions
from authentication.permissions import IsInstitutionAdmin, IsFaculty

# Serializers
from profiles.serializers import (
    HODCreateSerializer,
    HODListSerializer,
    StudentListSerializer,
)


# ---------------------------------------------------
# 1. HOD CREATE
# ---------------------------------------------------


class HODListCreateView(ListCreateAPIView):
    queryset = FacultyProfile.objects.filter(is_hod=True)
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]

    def get_serializer_class(self):
        if self.request.method in ["POST"]:
            return HODCreateSerializer
        return HODListSerializer


# ---------------------------------------------------
# 3. FACULTY MENTEE LIST
# ---------------------------------------------------
class FacultyMenteeListView(ListAPIView):
    """
    Lists all students mentored by the currently logged-in faculty member.
    """

    permission_classes = [IsAuthenticated, IsFaculty]
    serializer_class = StudentListSerializer

    def get_queryset(self):
        return StudentProfile.objects.filter(
            mentor=self.request.user.faculty_profile
        ).select_related("user", "department")
