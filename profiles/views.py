from django.shortcuts import render
from resume.services.get_student_details import generate_student_details
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from authentication.permissions import IsStudent
# Create your views here.

@permission_classes([IsAuthenticated,IsStudent])
@api_view(["GET"])
def get_student_data(request):
    return Response(generate_student_details(request.user))
