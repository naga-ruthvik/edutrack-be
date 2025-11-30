from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django_tenants.utils import schema_context

# Models
from customers.models import Institution, Domain
from authentication.models import User 

from .serializers import RegisterCollegeSerializer, InstitutionSerializer

class RegisterCollegeView(GenericAPIView):
    """
    Public Endpoint: Creates a new College (Tenant) AND the Principal (Admin User).
    URL: /public/register-college/
    """
    permission_classes = [] 
    serializer_class = RegisterCollegeSerializer

    def post(self, request):
        # 1. Automatic Validation
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 2. Extract Validated Data
        data = serializer.validated_data
        college_name = data['college_name']
        slug = data['slug']
        admin_email = data['admin_email']
        password = data['password']

        try:
            with transaction.atomic():
                # 3. Create Tenant (Schema)
                college = Institution(schema_name=slug, name=college_name)
                college.save()  # Triggers automatic schema creation

                # 4. Create Domain - Use slug directly for TenantSubfolderMiddleware
                # The domain field must match the schema_name for subfolder routing
                domain = Domain()
                domain.domain = slug  # FIXED: Use slug instead of f"{slug}.localhost"
                domain.tenant = college
                domain.is_primary = True  # Set as primary domain
                domain.save()
                
                # 5. Create Admin User INSIDE the new Schema
                with schema_context(college.schema_name):
                    user = User.objects.create_user(
                        email=admin_email,
                        username=admin_email,
                        password=password,
                        role='ADMIN', 
                        is_staff=True, 
                        is_superuser=True 
                    )

            return Response({
                "message": f"College '{college_name}' created successfully.",
                "login_url": f"/api/{slug}/auth/jwt/create/"
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ListCollegesView(ListAPIView):
    """
    Public Endpoint: Lists all colleges (tenants).
    URL: /public/list-colleges/
    """
    permission_classes = []
    serializer_class = InstitutionSerializer

    def get_queryset(self):
        return Institution.objects.exclude(schema_name='public')