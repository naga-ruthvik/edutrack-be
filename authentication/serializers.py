from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers
from .models import User
from profiles.models import StudentProfile, FacultyProfile

# 1. Serializer for Creating Users (Used by Djoser /users/)
class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        # We explicitly include 'role' so Djoser saves it
        fields = ('id', 'email', 'username', 'password', 'first_name', 'last_name', 'role')

# 2. Serializers for nested Profile Data
class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ['roll_number', 'batch_year', 'current_semester', 'department']

class FacultyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacultyProfile
        fields = ['employee_id', 'designation', 'is_hod', 'department']

# 3. Serializer for Viewing Current User (GET /users/me/)
class CurrentUserSerializer(BaseUserSerializer):
    profile = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'role', 'profile_picture', 'profile')

    def get_profile(self, obj):
        # Dynamically attach the correct profile data
        if obj.role == User.Role.STUDENT:
            try:
                return StudentProfileSerializer(obj.student_profile).data
            except StudentProfile.DoesNotExist:
                return None
        elif obj.role == User.Role.FACULTY:
            try:
                return FacultyProfileSerializer(obj.faculty_profile).data
            except FacultyProfile.DoesNotExist:
                return None
        return None