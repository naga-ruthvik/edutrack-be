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
from resume.services.resume_analyzer import analyze_resume
from rest_framework.views import APIView

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
        data = ResumeSerializer(resume).data
        data["tailored_content"] = resume.tailored_content

        return Response(    
            data,
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
    
class AnalyzeResumeAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get_object(self):
        resume = Resume.objects.filter(
            student=self.request.user.student_profile
        ).last()
        if not resume:
            from rest_framework.exceptions import NotFound
            raise NotFound("No resume found to analyze.")
        return resume

    def post(self, request, *args, **kwargs):
        resume = self.get_object()
        resume_details = resume.tailored_content

        jd_text = request.data.get("job_description", "")

        if not resume_details:
            return Response(
                {"error": "Resume details aren't present"},
                status=status.HTTP_400_BAD_REQUEST
            )

        resume_response = analyze_resume(resume_details, jd_text)

        return Response(resume_response, status=status.HTTP_200_OK)


class ResumeAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsStudent]
    serializer_class = ResumeSerializer
    lookup_field='pk'

    def get_object(self):
        resume = Resume.objects.filter(pk=self.kwargs['pk']).last()
        if not resume:
            from rest_framework.exceptions import NotFound
            raise NotFound("No resume found to analyze.")
        return resume

    def get(self, request, *args, **kwargs):
        resume = self.get_object()
        resume_details={}
        resume_details["tailored_content"] = resume.tailored_content
        # resume_details["id"] = resume.id

        if not resume_details:
            return Response(
                {"error": "Resume details aren't present"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(resume_details, status=status.HTTP_200_OK)


class ListResumeAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsStudent]
    serializer_class = ResumeSerializer
    def get_queryset(self):
        return Resume.objects.filter(student=self.request.user.student_profile)