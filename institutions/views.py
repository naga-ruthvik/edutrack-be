from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.http import FileResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.views import InstitutionFilterMixin
from users.models import Profile, User
from users.permissions import IsFaculty, IsHod, IsInstitutuionAdmin, IsStudent
from utils.generate_credentials import generate_usename_password

from .models import Department, Institution
from .serializers import ProfileSerializer, ProfileUploadSerializer
from django.http import HttpResponse
from django.core.files.base import ContentFile
# class AdminView(ListAPIView):
#     model=Institution
#     permission_classes=[IsFaculty]
#     def get_queryset(self):
#         return super().get_queryset()

class InstitutionStudentsAPIView(InstitutionFilterMixin, ListAPIView):
    """listing all students present in a institute"""
    model=Profile
    queryset = Profile.objects.filter(role='STUDENT')
    permission_classes=[IsAuthenticated,IsInstitutuionAdmin]
    serializer_class=ProfileSerializer

    # filter only students
    # def get_queryset(self):
    #     queryset = super().get_queryset()
    #     return queryset
    
class CreateProfilesView(GenericAPIView):
    """Creates students and profiles in bulk from an Excel file."""
    serializer_class = ProfileUploadSerializer
    parser_classes = [MultiPartParser, FormParser] # Required for file upload
    permission_classes = [IsAuthenticated, IsInstitutuionAdmin]

    def post(self, request, *args, **kwargs):
        # 1. Validate the incoming data (File, Role, Code)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        input_file = serializer.validated_data.get('file')
        role = serializer.validated_data.get('role').upper()
        college_code = serializer.validated_data.get('body') # Not used in logic, but retrieved

        # 2. Logic to process file
        # (Assuming generate_usename_password and model imports are correct)
        try:
            df, updated_file_obj = generate_usename_password(input_file,college_code)
            file_for_response = ContentFile(updated_file_obj.getvalue(), name="credentials.xlsx")

            print("--------------DF-------------", df.columns)
        except Exception as e:
            return Response({"error": f"Error processing file: {e}"}, status=400)

        institution_id = request.user.profile.institution

        # Mapping departments: Use .objects.filter, not .filter
        try:
            department_map = {
                dept.name: dept.id 
                for dept in Department.objects.filter(institution=institution_id)
            }
        except Exception as e:
             return Response({"error": "Failed to map departments."}, status=500)

        # List to collect errors for the final response
        error_rows = []

        # 3. ATOMIC DATABASE OPERATIONS
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # Explicit Validation and Error Handling
                    username = row.get("Username")
                    password = row.get("Password")
                    dept_name = row.get("Department")
                    print("username, password, department",username, password, dept_name)

                    if not username or not password or not dept_name:
                         raise ValueError("Missing essential data (Username, Password, or Department) in row.")

                    department_id = department_map.get(dept_name)
                    if not department_id:
                        raise ValueError(f"Department '{dept_name}' not found for your institution.")

                    print("-----------------creating user---------------")
                    # Create User (handles potential IntegrityError for duplicate username/email)
                    user = User.objects.create_user(
                        username=username,
                        email=row.get("Email",""),
                        first_name=row.get("First Name",""),
                        last_name=row.get("Last Name",""),
                        is_active=True,
                    )
                    user.set_password(password) 
                    user.save() 
                    print("-----------created user-----------",user)
                    # Create Profile
                    print("-----------created profile-----------")
                    Profile.objects.create(
                        user=user,
                        first_name=row.get("First Name",""),
                        last_name=row.get("Last Name",""),
                        identifier=row.get("Identifier",""),
                        department_id=department_id,
                        institution=institution_id,
                        role=role
                    )
                    
                except IntegrityError as e:
                    # Catch database errors like duplicate username/email
                    error_rows.append(f"Row {index + 2}: Duplicate User (Username or Email already exists).{e}")
                    
                except ValueError as ve:
                    # Catch custom validation errors (e.g., department not found)
                    error_rows.append(f"Row {index + 2}: Custom Error - {ve}",)
                    
                except Exception as e:
                    # Catch any other unexpected error
                    error_rows.append(f"Row {index + 2}: Unexpected Error - {e}")


        # 4. Final Response (Handle partial success/failure)
        if error_rows:
            # If there are errors, return a detailed list and a non-200 status
            return Response({"message": "Profiles created with errors.", "errors": error_rows}, status=400)
            
        if not updated_file_obj:
            return Response({"error": "Successfully created profiles, but output file could not be generated."}, status=500)

        response = HttpResponse(
            updated_file_obj.getvalue().decode(),
            content_type="text/csv"
        )
        response['Content-Disposition'] = 'attachment; filename="credentials.csv"'
        response['X-Message'] = 'File generated successfully'
        response['X-Status'] = 'success'

        return response