from django.urls import path
from .views import GenerateResumeAPIView, UpdateResumeAPIView

urlpatterns = [
    path('generate/', GenerateResumeAPIView.as_view(), name='generate-resume'),
    path('update/', UpdateResumeAPIView.as_view(), name='update-resume'),
]