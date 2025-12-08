# institutions/serializers.py (or academics/serializers.py)
from rest_framework import serializers
from authentication.models import User
from profiles.models import StudentProfile, FacultyProfile
from academics.models import Department
from profiles.models import Education

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
    department_id = serializers.ChoiceField(choices=[])
    username = serializers.CharField(required=False) # Optional, can derive from email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fields['department_id'].choices = list(Department.objects.values_list('id', 'code'))
        except Exception:
            pass

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role','phone_number','address','city','country','state','zipcode']

class StudentEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ['id', 'student', 'level', 'score','institution_name','board_or_university','passing_year','board_or_university','level','passing_year'] # Removed non-existent cgpa, percentage

class StudentDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    phone_number = serializers.CharField(source='user.phone_number')
    address = serializers.CharField(source='user.address')
    city = serializers.CharField(source='user.city')
    country = serializers.CharField(source='user.country')
    state = serializers.CharField(source='user.state')
    zipcode = serializers.CharField(source='user.zip_code') # Note: model has zip_code
    role = serializers.CharField(source='user.role')
    education=serializers.SerializerMethodField()

    def get_education(self,obj):
        return StudentEducationSerializer(obj.education_history.all(), many=True).data

    class Meta:
        model = StudentProfile
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 
                  'address', 'city', 'country', 'state', 'zipcode', 'role',
                  'roll_number', 'department', 'batch_year', 'current_semester', 'mentor','education']
                  