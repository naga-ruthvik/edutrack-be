from django.urls import path
from .views import GenerateResumeAPIView, UpdateResumeAPIView, AnalyzeResumeAPIView, ResumeAPIView, ListResumeAPIView, get_student_data
urlpatterns = [
    path('generate/', GenerateResumeAPIView.as_view(), name='generate-resume'),
    path('update/', UpdateResumeAPIView.as_view(), name='update-resume'),
    path('analyze/', AnalyzeResumeAPIView.as_view(), name='analyze-resume'),
    path('resume/<int:resume_id>/', ResumeAPIView.as_view(), name='resume'),
    path('resume/', ListResumeAPIView.as_view(), name='list-resume'),
    path('student/data/', get_student_data, name='list-student-data'),
]