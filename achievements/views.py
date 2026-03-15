from django.db import transaction, connection
from django.db.models import Count, Q, Sum
from rest_framework import status
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes

from authentication.models import User
from authentication.permissions import IsStudent, IsFaculty, IsInstitutionAdmin
from profiles.models import StudentProfile
from .models import Certificate
from .serializers import (
    CertificateUploadSerializer,
    CertificateListSerializer,
    CertificateVerificationSerializer,
)
from .tasks import process_certificate_verification
from utils.generate_presigned_url import generate_presigned_url


# ---------------------------------------------------
# 1. CERTIFICATE UPLOAD
# ---------------------------------------------------
class CertificateUploadView(GenericAPIView):
    """
    Uploads a certificate file, saves to S3, and triggers
    async AI verification via Celery.
    """

    permission_classes = [IsAuthenticated, IsStudent]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = CertificateUploadSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            try:
                # 1. Save to DB → auto-upload to S3 via model FileField
                certificate = serializer.save(student=request.user.student_profile)

                # 2. Generate presigned URL for the Celery worker
                object_key = certificate.file_url.name
                presigned_url = generate_presigned_url(object_key)

                if not presigned_url:
                    raise Exception("Failed to generate secure access URL")

                # 3. Trigger async verification in the correct tenant schema
                schema_name = connection.schema_name
                transaction.on_commit(
                    lambda: process_certificate_verification.delay(
                        presigned_url, certificate.id, schema_name
                    )
                )

                return Response(
                    {
                        "status": "Verification started",
                        "certificate_id": certificate.id,
                    },
                    status=status.HTTP_201_CREATED,
                )

            except Exception as e:
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------
# 2. CERTIFICATE LIST
# ---------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def certificate_list_view(request):
    """
    Returns certificates scoped by role:
    - Student: own certificates only
    - Faculty: certificates of mentees
    - Admin: all certificates
    """
    user = request.user

    if user.role == User.Role.STUDENT:
        certificates = Certificate.objects.filter(
            student=user.student_profile
        ).select_related("student", "student__user", "verified_by")

    elif user.role == User.Role.FACULTY:
        certificates = Certificate.objects.filter(
            student__mentor=user.faculty_profile
        ).select_related("student", "student__user", "verified_by")

    else:
        certificates = Certificate.objects.all().select_related(
            "student", "student__user", "verified_by"
        )

    serializer = CertificateListSerializer(certificates, many=True)
    return Response(serializer.data)


# ---------------------------------------------------
# 3. CERTIFICATE VERIFY (Faculty only)
# ---------------------------------------------------
@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsFaculty])
def certificate_verify_view(request, pk):
    """
    Allows a faculty mentor to verify or reject a certificate.
    Only the student's assigned mentor can verify.
    """
    serializer = CertificateVerificationSerializer(data=request.data)
    if serializer.is_valid():
        new_status = serializer.validated_data["status"]

        try:
            certificate = Certificate.objects.get(id=pk)

            if certificate.student.mentor != request.user.faculty_profile:
                return Response(
                    {"error": "You are not the mentor for this student."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            certificate.status = new_status
            certificate.verified_by = request.user.faculty_profile
            certificate.save()

            return Response(
                {"status": "Certificate status updated successfully"},
                status=status.HTTP_200_OK,
            )
        except Certificate.DoesNotExist:
            return Response(
                {"error": "Certificate not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------
# 4. CERTIFICATE DETAIL
# ---------------------------------------------------
class CertificateDetailView(RetrieveAPIView):
    """
    Retrieve a single certificate by PK.
    """

    serializer_class = CertificateListSerializer
    lookup_field = "pk"
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.select_related(
            "student", "student__user", "verified_by"
        )


# ---------------------------------------------------
# 5. TOTAL CREDIT POINTS
# ---------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsInstitutionAdmin])
def total_score_view(request):
    """
    Returns the total credit points across all certificates in the institution.
    """
    total = Certificate.objects.aggregate(total_score=Sum("credit_points"))[
        "total_score"
    ]
    return Response({"total_score": total or 0})


# ---------------------------------------------------
# 6. STUDENT ACHIEVEMENT SUMMARY
# ---------------------------------------------------
def _build_category_counts(certificates_qs):
    """
    Returns a dict of {category_lower: count} from a single aggregated query
    instead of 8 separate .count() calls.
    """
    counts = certificates_qs.values("category").annotate(count=Count("id"))
    result = {cat.lower(): 0 for cat, _ in Certificate.Category.choices}
    for row in counts:
        key = row["category"].lower()
        if key in result:
            result[key] = row["count"]
    return result


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_achievements_view(request):
    """
    - Student: returns own achievement counts by category
    - Faculty: returns achievement counts for each mentee
    """
    if request.user.role == User.Role.STUDENT:
        student = request.user.student_profile
        certs = Certificate.objects.filter(student=student)
        certificates_data = _build_category_counts(certs)

        return Response(
            {
                "roll_number": student.roll_number,
                "certificates": certificates_data,
            }
        )

    elif request.user.role == User.Role.FACULTY:
        faculty = request.user.faculty_profile
        mentees = faculty.mentees.select_related("user").all()
        students_data = []

        for student in mentees:
            certs = Certificate.objects.filter(student=student)
            certificates_data = _build_category_counts(certs)

            students_data.append(
                {
                    "student_name": student.user.get_full_name(),
                    "roll_number": student.roll_number,
                    "certificates": certificates_data,
                }
            )

        return Response(students_data)

    return Response({"error": "Invalid Role"}, status=status.HTTP_400_BAD_REQUEST)
