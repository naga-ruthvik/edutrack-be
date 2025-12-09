from django.shortcuts import render
from .tasks import sync_data_task
from rest_framework.response import Response
from rest_framework.decorators import api_view
# Create your views here.

@api_view(['GET'])
def sync_data(request):
    sync_data_task.delay()
    return Response("Data sync started successfully.")