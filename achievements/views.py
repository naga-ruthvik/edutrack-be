from django.shortcuts import render
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from .serializers import CertificateUploadSerializer, CertificateListSerializer, CertificateVerificationSerializer
from rest_framework.response import Response
from .tasks import process_certificate_verification
# Create your views here.
from django.db import transaction, connection
from rest_framework import status
from authentication.permissions import IsStudent, IsFaculty
from rest_framework.decorators import permission_classes, api_view
from utils.generate_presigned_url import generate_presigned_url  # Import 
from authentication.models import User
from .models import Certificate

from rest_framework.parsers import MultiPartParser, FormParser

class CertificateUploadAPIView(GenericAPIView):
    permission_classes = [IsAuthenticated, IsStudent]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = CertificateUploadSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # We pass the student (user profile) here because it's not in the request data
            try:
                # 1. Save to DB and automatically upload to S3 via the Model Field
                certificate = serializer.save(student=request.user.student_profile)
                
                # 2. Generate Presigned URL
                # certificate.file.name contains the S3 Object Key (e.g. "certificates/student_1/doc.pdf")
                object_key = certificate.file_url.name
                presigned_url = generate_presigned_url(object_key)
                
                if not presigned_url:
                    raise Exception("Failed to generate secure access URL")

                # 3. Trigger Celery Task with the secure Presigned URL
                # Pass schema_name to ensure task runs in correct tenant context
                schema_name = connection.schema_name
                transaction.on_commit(
                    lambda: process_certificate_verification.delay(presigned_url, certificate.id, schema_name)
                )

                return Response({
                    "status": "Verification started",
                    "certificate_id": certificate.id
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                # Catch S3 upload errors or DB errors
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 4. Return errors if data was bad
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated])
@api_view(['GET'])
def list_certificates(request):

    user = request.user
    print("ROLE:", request.user.role)
    print("FAC:", User.Role.FACULTY)
    print("STU:", User.Role.STUDENT)

    if user.role == User.Role.STUDENT:
        # Student → only THEIR certificates
        certificates = Certificate.objects.filter(
            student=user.student_profile
        ).select_related("student", "student__user", "verified_by")

    elif user.role == User.Role.FACULTY:
        # Faculty → certificates of ALL students under this mentor
        certificates = Certificate.objects.filter(
            student__mentor=user.faculty_profile
        ).select_related("student", "student__user", "verified_by")

    else:
        # Admin/HOD → all certificates
        certificates = Certificate.objects.all().select_related(
            "student", "student__user", "verified_by"
        )
    
    serializer = CertificateListSerializer(certificates, many=True)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsFaculty])
def verify_certificates(request, pk):
    serializer = CertificateVerificationSerializer(data=request.data)
    if serializer.is_valid():
        new_status = serializer.validated_data['status']
        
        try:
            certificate = Certificate.objects.get(id=pk)
            
            # Faculty checks: Must be the mentor of the student
            if certificate.student.mentor != request.user.faculty_profile:
                 return Response({"error": "You are not the mentor for this student."}, status=status.HTTP_403_FORBIDDEN)

            certificate.status = new_status
            certificate.verified_by = request.user.faculty_profile
            certificate.save()
            
            return Response({"status": "Certificate status updated successfully"}, status=status.HTTP_200_OK)
        except Certificate.DoesNotExist:
            return Response({"error": "Certificate not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
             
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CertificateRetrieveAPIView(RetrieveAPIView):
    serializer_class = CertificateListSerializer
    lookup_field = "pk"
    permission_classes=[IsAuthenticated]
    def get_object(self):
        return Certificate.objects.get(id=self.kwargs["pk"])
