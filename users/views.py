from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import InstitutionAdminCreateSerializer

class InstitutionRegisterView(APIView):
    """
    A custom public endpoint for a new Institution Admin to register.
    This creates the Institution, the Admin User, and the Admin Profile.
    """
    permission_classes = [AllowAny] # Anyone can access this endpoint to sign up
    serializer_class = InstitutionAdminCreateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # The .perform_create() logic from our serializer
            # will be called by Djoser's logic which we are 
            # leveraging within the serializer.
            # We need to manually call the save logic here.
            
            # Let's adjust the serializer logic slightly
            # In InstitutionAdminCreateSerializer, rename 'perform_create' to 'save'
            # (I'll show this in Step 3)
            
            user = serializer.save()
            
            # We can return a success message or even auto-login tokens
            # For now, a simple success message is good.
            return Response(
                {"message": "Institution and Admin created successfully."},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)