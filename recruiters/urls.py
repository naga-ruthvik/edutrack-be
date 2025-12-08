from .views import JobPostingList, ListApplicationsAPIView
from django.urls import path

urlpatterns = [
    path('job-postings/', JobPostingList.as_view(), name='job-posting-list'),
    path('applications/', ListApplicationsAPIView.as_view(), name='application-list'),
]