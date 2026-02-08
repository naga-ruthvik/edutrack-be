from django.shortcuts import render
from .tasks import run_full_sync
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django_tenants.utils import schema_context
# Create your views here.

@api_view(['GET'])
def sync_data(request):
    with schema_context(request.tenant.schema_name):
        run_full_sync.delay(request.tenant.schema_name)
    return Response("Data sync started successfully.")