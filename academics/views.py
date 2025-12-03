# institutions/views.py (or move to academics/views.py)

import pandas as pd
import random
import string
from io import BytesIO
from django.db import transaction, IntegrityError
from django.http import HttpResponse
from django.core.files.base import ContentFile
from rest_framework.generics import GenericAPIView, ListAPIView, CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

# Models
from authentication.models import User
from profiles.models import StudentProfile, FacultyProfile
from .models import Department

# Permissions
from authentication.permissions import IsInstitutionAdmin, IsFaculty # Assuming you created these

# Serializers
from .serializers import (
    BulkProfileUploadSerializer, 
    CreateDepartmentSerializer, 
    CreateHODSerializer, 
    HODSerializer,
    DepartmentSerializer
)

# Utilities
from utils.generate_credentials import create_college_username, create_custom_password, save_data

# ---------------------------------------------------
# 1. LIST STUDENTS (Refactored)
# ---------------------------------------------------
class InstitutionStudentsAPIView(ListAPIView):
    """
    Lists all students in the CURRENT tenant.
    No mixin needed. Schema handles isolation.
    """
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]
    # Serializer needed for response (you can reuse the one from users app)
    from authentication.serializers import StudentProfileSerializer 
    serializer_class = StudentProfileSerializer

    def get_queryset(self):
        # Simply return all. The DB Schema limits this to the current college.
        return StudentProfile.objects.select_related('user', 'department').all()


# 2. BULK UPLOAD (Heavy Refactor)
class CreateBulkProfilesView(GenericAPIView):
    serializer_class = BulkProfileUploadSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]

    def generate_random_password(self, length=10):
        """Generate a random password with letters, numbers, and special characters"""
        characters = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(random.choice(characters) for _ in range(length))

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        input_file = serializer.validated_data['file']
        role = serializer.validated_data['role']
        print(role)
        
        # Read Excel
        try:
            df = pd.read_excel(input_file) if input_file.name.endswith(('.xlsx', '.xls')) else pd.read_csv(input_file)
        except Exception as e:
            return Response({"error": f"Failed to read file: {e}"}, status=400)

        error_rows = []
        created_count = 0
        credentials_data = []  # Track credentials for Excel export
        print(df['Department'])
        # Pre-fetch departments to avoid N+1 queries
        # Map Name -> ID (e.g., "CSE" -> 5)
        dept_map = {d.code.lower(): d for d in Department.objects.all()}
        print(dept_map)
        # Get college code - using default for now
        college_code = "88"  # You can make this configurable

        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    email = row.get('Email')
                    first_name = row.get('First Name')
                    last_name = row.get('Last Name', '')
                    dept_name = str(row.get('Department', '')).lower()
                    roll_number = row.get('Roll Number')
                    
                    if not email or not dept_name:
                        error_rows.append(f"Row {index + 2}: Missing email or department")
                        continue # Skip bad rows

                    # 2. Get Department
                    print("dept_name:  ",dept_name)
                    department = dept_map.get(dept_name)
                    print("department:  ",department)
                    if not department:
                        error_rows.append(f"Row {index + 2}: Department '{dept_name}' not found")
                        continue

                    # Generate credentials based on role
                    if role == 'STUDENT':
                        # For students: Use roll number as username
                        username = str(roll_number)
                        password = self.generate_random_password()
                        
                    elif role == 'FACULTY':
                        # For faculty: Generate custom username and password
                        employee_id = row.get('Employee ID', f"TEMP-{index}")
                        
                        # Create a temporary row dict for the utility functions
                        temp_row = pd.Series({
                            'Identifier': employee_id,
                            'First Name': first_name,
                            'Last Name': last_name,
                            'Department': department
                        })
                        
                        # Generate username using utility function
                        username = create_college_username(
                            temp_row, 
                            'Identifier', 
                            'Department', 
                            college_code
                        )
                        
                        # Generate password using utility function
                        password = create_custom_password(temp_row, 'First Name')
                    else:
                        error_rows.append(f"Row {index + 2}: Invalid role")
                        continue

                    # 1. Create User
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        role=role
                    )

                    # 3. Create Specific Profile
                    print(f"adding {role} profile")
                    if role == 'STUDENT':
                        # Manually create StudentProfile
                        profile = StudentProfile.objects.create(
                            user=user,
                            roll_number=roll_number,
                            department=department,
                            batch_year=2024,  # You may want to get this from the file
                            current_semester=1
                        )
                        print("created student profile")
                        
                        # Track credentials
                        credentials_data.append({
                            'Email': email,
                            'First Name': first_name,
                            'Last Name': last_name,
                            'Username': username,
                            'Password': password,
                            'Role': 'Student',
                            'Department': department,
                            'Roll Number': roll_number,
                            'Status': 'Success'
                        })
                    
                    elif role == 'FACULTY':
                        # Manually create FacultyProfile
                        employee_id = row.get('Employee ID', f"TEMP-{user.id}")
                        profile = FacultyProfile.objects.create(
                            user=user,
                            employee_id=employee_id,
                            department=department,
                            designation=row.get('Designation', 'ASST_PROF')
                        )
                        
                        # Track credentials
                        credentials_data.append({
                            'Email': email,
                            'First Name': first_name,
                            'Last Name': last_name,
                            'Username': username,
                            'Password': password,
                            'Role': 'Faculty',
                            'Department': department,
                            'Employee ID': employee_id,
                            'Status': 'Success'
                        })

                    created_count += 1

                except Exception as e:
                    error_msg = f"Row {index + 2}: {str(e)}"
                    error_rows.append(error_msg)
                    
                    # Track failed row in credentials if we have basic info
                    if 'email' in locals() and email:
                        credentials_data.append({
                            'Email': email,
                            'First Name': first_name if 'first_name' in locals() else '',
                            'Last Name': last_name if 'last_name' in locals() else '',
                            'Username': '',
                            'Password': '',
                            'Role': role,
                            'Department': dept_name if 'dept_name' in locals() else '',
                            'Roll Number/Employee ID': roll_number if 'roll_number' in locals() else '',
                            'Status': f'Failed: {str(e)}'
                        })

        # Generate Excel file with credentials
        if credentials_data:
            credentials_df = pd.DataFrame(credentials_data)
            
            # Create Excel file in memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                credentials_df.to_excel(writer, sheet_name='Credentials', index=False)
                
                # Add errors sheet if there are errors
                if error_rows:
                    errors_df = pd.DataFrame({'Errors': error_rows})
                    errors_df.to_excel(writer, sheet_name='Errors', index=False)
            
            output.seek(0)
            
            # Return Excel file as HTTP response
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=bulk_upload_credentials_{role.lower()}.xlsx'
            
            return response
        else:
            # No profiles were created, return JSON error response
            return Response({
                "error": "No profiles were created",
                "errors": error_rows
            }, status=400)

# ---------------------------------------------------
# 3. CREATE DEPARTMENT (Refactored)
# ---------------------------------------------------
class CreateDepartmentAPIView(CreateAPIView):
    queryset = Department.objects.all()
    serializer_class = CreateDepartmentSerializer
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]

    def perform_create(self, serializer):
        # No need to set institution=... it lives in the tenant schema
        serializer.save()

# ---------------------------------------------------
# 4. CREATE HOD (Refactored)
# ---------------------------------------------------
class CreateHOD_APIView(GenericAPIView):
    serializer_class = CreateHODSerializer
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                # 1. Create User
                user = User.objects.create_user(
                    email=data['email'],
                    username=data.get('username', data['email']),
                    password=data['password'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    role=User.Role.FACULTY # HOD is a Faculty first
                )

                profile = FacultyProfile.objects.create(
                    user=user,
                    employee_id=data.get('employee_id', f"HOD-{user.id}"),
                    department_id=data['department_id'],
                    designation=data.get('designation', 'PROFESSOR'),
                    is_hod=True
                )

                return Response({"message": "HOD Created", "id": user.id}, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

# ---------------------------------------------------
# 5. LIST HODs (Refactored)
# ---------------------------------------------------
class ListHOD_APIView(ListAPIView):
    serializer_class = HODSerializer
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]

    def get_queryset(self):
        # Filter Faculty where is_hod = True
        return FacultyProfile.objects.filter(is_hod=True)