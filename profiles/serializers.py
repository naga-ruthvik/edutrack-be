from rest_framework import serializers
from authentication.models import User
from profiles.models import StudentProfile, FacultyProfile, Education
from academics.models import Department


# USER SERIALIZERS
class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
        ]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "role",
            "phone_number",
            "address",
            "city",
            "country",
            "state",
            "zip_code",
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "password",
        ]


class BulkProfileUploadSerializer(serializers.Serializer):
    """
    Validates Excel upload for bulk student/faculty creation.
    """

    file = serializers.FileField()
    role = serializers.ChoiceField(choices=["STUDENT", "FACULTY"])

    def validate_file(self, value):
        if not value.name.endswith((".xlsx", ".xls", ".csv")):
            raise serializers.ValidationError("Invalid file type.")
        return value


# FACULTY SERIALIZERS
class HODListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.get_full_name")
    email = serializers.EmailField(source="user.email")
    department = serializers.SerializerMethodField()

    class Meta:
        model = FacultyProfile
        fields = ["employee_id", "full_name", "email", "department"]

    def get_department(self, obj):
        return obj.department.code if obj.department else None


class CreateHODSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    department_id = serializers.ChoiceField(choices=[])
    username = serializers.CharField(required=False)  # Optional, can derive from email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fields["department_id"].choices = list(
                Department.objects.values_list("id", "code")
            )
        except Exception:
            pass


class FacultyProfileSerializer(serializers.ModelSerializer):
    """
    Used for listing/retrieving faculty profiles with nested user data.
    """

    user = UserSerializer(read_only=True)

    class Meta:
        model = FacultyProfile
        fields = ["id", "employee_id", "designation", "is_hod", "department", "user"]


# STUDENT SERIALIZERS
class StudentEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            "id",
            "student",
            "level",
            "score",
            "institution_name",
            "board_or_university",
            "passing_year",
        ]


class StudentDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email")
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    phone_number = serializers.CharField(source="user.phone_number")
    address = serializers.CharField(source="user.address")
    city = serializers.CharField(source="user.city")
    country = serializers.CharField(source="user.country")
    state = serializers.CharField(source="user.state")
    zip_code = serializers.CharField(source="user.zip_code")
    role = serializers.CharField(source="user.role")
    education = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()

    def get_skills(self, obj):
        return obj.skills.all().values_list("name", flat=True)

    def get_education(self, obj):
        return StudentEducationSerializer(obj.education_history.all(), many=True).data

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "address",
            "city",
            "country",
            "state",
            "zip_code",
            "role",
            "roll_number",
            "department",
            "batch_year",
            "current_semester",
            "mentor",
            "education",
            "skills",
        ]


class StudentListSerializer(serializers.ModelSerializer):
    """
    Used for listing/retrieving student profiles with nested user data.
    """

    user = UserListSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "roll_number",
            "batch_year",
            "current_semester",
            "department",
            "user",
        ]


class StudentCreateSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer()
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())

    class Meta:
        model = StudentProfile
        fields = ["user", "roll_number", "department", "batch_year", "current_semester"]

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        roll_number = validated_data["roll_number"]
        user = User.objects.create_user(
            **user_data, role=User.Role.STUDENT, username=roll_number
        )
        student = StudentProfile.objects.create(user=user, **validated_data)
        return student
