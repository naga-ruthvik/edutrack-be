from django.shortcuts import render
from rest_framework import generics
from authentication.permissions import IsRecruiter
from .models import JobPosting
from .serializers import JobPostingSerializer, ApplicationSerializer
# Create your views here.
class JobPostingList(generics.ListCreateAPIView):
    permission_classes = [IsRecruiter]
    serializer_class = JobPostingSerializer

    def get_queryset(self):
        return JobPosting.objects.filter(organization=self.request.user.recruiter_profile.organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.recruiter_profile.organization)

class ListApplicationsAPIView(generics.ListAPIView):
    permission_classes = [IsRecruiter]
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        return Application.objects.filter(job__organization=self.request.user.recruiter_profile.organization)