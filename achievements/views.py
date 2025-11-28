from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from .serilaizers import CertificateUploadSerializer
from rest_framework.response import Response
from .tasks import process_certificate_verification
# Create your views here.
from django.db import transaction
from rest_framework import status

class CertificateUploadAPIView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CertificateUploadSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # We pass the student (user profile) here because it's not in the request data
            try:
                # This saves to DB and automatically uploads to S3 via the Model Field
                certificate = serializer.save(student=request.user.profile)
                
                # This ensures the DB transaction is finished before Celery tries to read the record
                transaction.on_commit(
                    lambda: process_certificate_verification.delay(certificate.id,"kondenagaruthvik")
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