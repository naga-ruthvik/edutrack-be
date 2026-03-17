from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import (
    CreateAPIView,
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Models
from authentication.models import User

# Permissions
from authentication.permissions import IsInstitutionAdmin, IsStudent, IsStudentOrFaculty
from profiles.models import StudentProfile

# Serializers
from profiles.serializers import (
    StudentCreateSerializer,
    StudentDetailSerializer,
    StudentListSerializer,
)

# Services
from resume.services.get_student_details import (
    generate_student_details,
    prefetch_user_for_resume,
)


class StudentListCreateView(GenericAPIView):
    queryset = StudentProfile.objects.all()

    def get_serializer_class(self):
        if self.request.method in ["POST"]:
            return StudentCreateSerializer
        return StudentListSerializer

    def get_permission_classes(self):
        if self.request.method in ["POST"]:
            return [IsInstitutionAdmin]
        return [IsAuthenticated]

    def get(self, request):
        students = self.get_queryset()
        serializer = self.get_serializer(students, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        return Response(
            StudentListSerializer(student).data, status=status.HTTP_201_CREATED
        )


# ---------------------------------------------------
# 2. STUDENT DETAIL (by PK)
# ---------------------------------------------------
class StudentDetailView(RetrieveAPIView):
    """
    Retrieve a single student profile by PK.
    Accessible to Students and Faculty.
    """

    permission_classes = [IsAuthenticated, IsStudentOrFaculty]
    serializer_class = StudentDetailSerializer
    lookup_field = "pk"

    def get_queryset(self):
        return StudentProfile.objects.select_related("user", "department").all()


# ---------------------------------------------------
# 5. TOTAL STUDENTS COUNT
# ---------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsInstitutionAdmin])
def student_total_view(request):
    """
    Returns the total number of students in the institution.
    """
    count = StudentProfile.objects.count()
    return Response({"total_students": count})


# ---------------------------------------------------
# 7. STUDENT DATA (aggregated profile + education + skills)
# ---------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def student_data_view(request):
    """
    Returns aggregated student details for resume / profile view.
    """
    user = prefetch_user_for_resume(User.objects.filter(id=request.user.id)).first()
    return Response(generate_student_details(user))
