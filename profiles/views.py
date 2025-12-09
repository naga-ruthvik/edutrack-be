from django.shortcuts import render
from resume.services.get_student_details import generate_student_details
from rest_framework.response import Response
from rest_framework.decorators import api_view
# Create your views here.

@api_view(["GET"])
def get_student_data(request):
    return Response(generate_student_details(request.user))
