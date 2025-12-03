from django.shortcuts import render
from rest_framework import generics
from .serializers import ResumeSerializer, UpdateResumeSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from resume.services.resume_generator import generate_resume_service
from resume.services.get_student_details import generate_student_details
from authentication.permissions import IsStudent 
from .models import Resume

class GenerateResumeAPIView(generics.GenericAPIView):
    serializer_class = ResumeSerializer
    permission_classes = [IsAuthenticated,IsStudent] 

    def perform_create(self, serializer):
        serializer.save(student=self.request.user.student_profile)
    
    def post(self, request, *args, **kwargs):
        print("received post request")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create resume with student set
        resume = serializer.save(student=request.user.student_profile)

        # Extract JD
        jd_text = serializer.validated_data.get('job_description', "")

        # Student details
        resume_text = generate_student_details(self.request.user)

        # Generate tailored resume
        resume_response = generate_resume_service(resume_text=resume_text, jd_text=jd_text)

        resume.tailored_content = resume_response
        resume.save()

        return Response(
            ResumeSerializer(resume).data,
        status=status.HTTP_201_CREATED
        )


class UpdateResumeAPIView(generics.UpdateAPIView):
    serializer_class = UpdateResumeSerializer
    permission_classes = [IsAuthenticated,IsStudent]

    def get_object(self):
        # Get the latest resume for the current student
        resume = Resume.objects.filter(student=self.request.user.student_profile).last()
        if not resume:
            from rest_framework.exceptions import NotFound
            raise NotFound("No resume found to update.")
        return resume

    def patch(self, request, *args, **kwargs):
        resume = self.get_object()
        serializer = self.get_serializer(resume, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        tailored_content = serializer.validated_data.get('tailored_content')

        if not tailored_content:
            return Response(
                {"error": "Tailored content is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

        return Response(
            ResumeSerializer(resume).data,
            status=status.HTTP_200_OK
        )
    
