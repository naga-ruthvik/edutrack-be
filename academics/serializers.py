# institutions/serializers.py (or academics/serializers.py)
from rest_framework import serializers
from authentication.models import User
from profiles.models import StudentProfile, FacultyProfile
from .models import Department

class InstitutionCreateSerializer(serializers.Serializer):
    """
    Used by the Public API to register a new college.
    """
    name = serializers.CharField()
    slug = serializers.CharField()
    logo = serializers.ImageField(required=False)
    # Add address fields if needed...

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'code']

class CreateDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['name', 'code']

class BulkProfileUploadSerializer(serializers.Serializer):
    """
    Validates Excel upload.
    """
    file = serializers.FileField()
    role = serializers.ChoiceField(choices=['STUDENT', 'FACULTY'])
    # No 'body' (college code) needed, the URL determines the college.

    def validate_file(self, value):
        if not value.name.endswith(('.xlsx', '.xls', '.csv')):
            raise serializers.ValidationError("Invalid file type.")
        return value

class HODSerializer(serializers.ModelSerializer):
    """
    For Listing HODs.
    """
    full_name = serializers.CharField(source='user.get_full_name')
    email = serializers.EmailField(source='user.email')
    department = serializers.CharField(source='department.code')

    class Meta:
        model = FacultyProfile
        fields = ['employee_id', 'full_name', 'email', 'department']

class CreateHODSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    department_id = serializers.IntegerField()
    username = serializers.CharField(required=False) # Optional, can derive from email