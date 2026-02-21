import pandas as pd
import random
import string
from io import BytesIO
from django.db import transaction
from django.http import HttpResponse
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

# Models
from authentication.models import User
from profiles.models import StudentProfile, FacultyProfile
from academics.models import Department

# Permissions
from authentication.permissions import IsInstitutionAdmin

# Serializers
from profiles.serializers import BulkProfileUploadSerializer

# Utilities
from utils.generate_credentials import (
    create_college_username,
    create_custom_password,
)


class BulkProfileUploadView(GenericAPIView):
    """
    Accepts a CSV/Excel file and creates User + StudentProfile/FacultyProfile
    records in bulk. Returns an Excel file with generated credentials.
    """

    serializer_class = BulkProfileUploadSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, IsInstitutionAdmin]

    def generate_random_password(self, length=10):
        """Generate a random password with letters, numbers, and special characters."""
        characters = string.ascii_letters + string.digits + "!@#$%"
        return "".join(random.choice(characters) for _ in range(length))

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        input_file = serializer.validated_data["file"]
        role = serializer.validated_data["role"]

        # Read Excel/CSV
        try:
            df = (
                pd.read_excel(input_file)
                if input_file.name.endswith((".xlsx", ".xls"))
                else pd.read_csv(input_file)
            )
        except Exception as e:
            return Response({"error": f"Failed to read file: {e}"}, status=400)

        error_rows = []
        created_count = 0
        credentials_data = []

        # Pre-fetch departments to avoid N+1 queries
        dept_map = {d.code.lower(): d for d in Department.objects.all()}

        # College code - make this configurable later
        college_code = "88"

        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    email = row.get("Email")
                    first_name = row.get("First Name")
                    last_name = row.get("Last Name", "")
                    dept_name = str(row.get("Department", "")).lower()
                    roll_number = row.get("Roll Number")

                    if not email or not dept_name:
                        error_rows.append(
                            f"Row {index + 2}: Missing email or department"
                        )
                        continue

                    department = dept_map.get(dept_name)
                    if not department:
                        error_rows.append(
                            f"Row {index + 2}: Department '{dept_name}' not found"
                        )
                        continue

                    # Generate credentials based on role
                    if role == User.Role.STUDENT:
                        username = str(roll_number)
                        password = self.generate_random_password()

                    elif role == User.Role.FACULTY:
                        employee_id = row.get("Employee ID", f"TEMP-{index}")
                        temp_row = pd.Series(
                            {
                                "Identifier": employee_id,
                                "First Name": first_name,
                                "Last Name": last_name,
                                "Department": department,
                            }
                        )
                        username = create_college_username(
                            temp_row, "Identifier", "Department", college_code
                        )
                        password = create_custom_password(temp_row, "First Name")
                    else:
                        error_rows.append(f"Row {index + 2}: Invalid role")
                        continue

                    # Create User
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        role=role,
                    )

                    # Create Profile
                    if role == User.Role.STUDENT:
                        StudentProfile.objects.create(
                            user=user,
                            roll_number=roll_number,
                            department=department,
                            batch_year=2024,
                            current_semester=1,
                        )
                        credentials_data.append(
                            {
                                "Email": email,
                                "First Name": first_name,
                                "Last Name": last_name,
                                "Username": username,
                                "Password": password,
                                "Role": "Student",
                                "Department": department,
                                "Roll Number": roll_number,
                                "Status": "Success",
                            }
                        )

                    elif role == User.Role.FACULTY:
                        employee_id = row.get("Employee ID", f"TEMP-{user.id}")
                        FacultyProfile.objects.create(
                            user=user,
                            employee_id=employee_id,
                            department=department,
                            designation=row.get("Designation", "ASST_PROF"),
                        )
                        credentials_data.append(
                            {
                                "Email": email,
                                "First Name": first_name,
                                "Last Name": last_name,
                                "Username": username,
                                "Password": password,
                                "Role": "Faculty",
                                "Department": department,
                                "Employee ID": employee_id,
                                "Status": "Success",
                            }
                        )

                    created_count += 1

                except Exception as e:
                    error_msg = f"Row {index + 2}: {str(e)}"
                    error_rows.append(error_msg)

                    if "email" in locals() and email:
                        credentials_data.append(
                            {
                                "Email": email,
                                "First Name": first_name
                                if "first_name" in locals()
                                else "",
                                "Last Name": last_name
                                if "last_name" in locals()
                                else "",
                                "Username": "",
                                "Password": "",
                                "Role": role,
                                "Department": dept_name
                                if "dept_name" in locals()
                                else "",
                                "Roll Number/Employee ID": roll_number
                                if "roll_number" in locals()
                                else "",
                                "Status": f"Failed: {str(e)}",
                            }
                        )

        # Generate Excel file with credentials
        if credentials_data:
            credentials_df = pd.DataFrame(credentials_data)
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                credentials_df.to_excel(writer, sheet_name="Credentials", index=False)
                if error_rows:
                    errors_df = pd.DataFrame({"Errors": error_rows})
                    errors_df.to_excel(writer, sheet_name="Errors", index=False)

            output.seek(0)
            response = HttpResponse(
                output.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = (
                f"attachment; filename=bulk_upload_credentials_{role.lower()}.xlsx"
            )
            return response
        else:
            return Response(
                {"error": "No profiles were created", "errors": error_rows}, status=400
            )
