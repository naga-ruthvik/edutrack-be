from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

# Models
from authentication.models import User
from profiles.models import StudentProfile

# Permissions
from authentication.permissions import IsInstitutionAdmin, IsStudent, IsStudentOrFaculty

# Serializers
from profiles.serializers import StudentProfileSerializer, StudentDetailSerializer

# Services
from resume.services.get_student_details import generate_student_details


# ---------------------------------------------------
# 1. LIST ALL STUDENTS (Admin only)
# ---------------------------------------------------
class StudentListView(ListAPIView):
    """
    Lists all students in the CURRENT tenant.
    Schema handles tenant isolation.
    """

    permission_classes = [IsAuthenticated, IsInstitutionAdmin]
    serializer_class = StudentProfileSerializer

    def get_queryset(self):
        return StudentProfile.objects.select_related("user", "department").all()


# ---------------------------------------------------
# 2. STUDENT PROFILE LIST (for Students)
# ---------------------------------------------------
class StudentProfileListView(ListAPIView):
    """
    Lists all student profiles — accessible to authenticated students.
    """

    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        return StudentProfile.objects.select_related("user", "department").all()


# ---------------------------------------------------
# 3. STUDENT DETAIL (by PK)
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
# 4. CREATE STUDENT (Admin)
# ---------------------------------------------------
class StudentCreateView(CreateAPIView):
    """
    Create a new student profile. Admin only.
    """

    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]


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
# 6. LIST ALL STUDENTS (Admin — simple list)
# ---------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsInstitutionAdmin])
def student_list_all_view(request):
    """
    Returns all students. Requires admin authentication.
    """
    students = StudentProfile.objects.select_related("user", "department").all()
    return Response(StudentProfileSerializer(students, many=True).data)


# ---------------------------------------------------
# 7. STUDENT DATA (aggregated profile + education + skills)
# ---------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def student_data_view(request):
    """
    Returns aggregated student details for resume / profile view.
    """
    return Response(generate_student_details(request.user))
