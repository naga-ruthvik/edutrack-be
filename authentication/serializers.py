from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers
from .models import User
from profiles.models import StudentProfile, FacultyProfile

from profiles.serializers import StudentProfileSerializer, FacultyProfileSerializer


class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = (
            "id",
            "email",
            "username",
            "password",
            "first_name",
            "last_name",
            "role",
        )


class CurrentUserSerializer(BaseUserSerializer):
    profile = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "role",
            "profile_picture",
            "profile",
        )

    def get_profile(self, obj):
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
