from rest_framework import serializers
from .models import JobPosting, Organization, Application, RecruiterProfile

class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = '__all__'

from profiles.models import StudentProfile, Education

class StudentDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.get_full_name')
    email = serializers.EmailField(source='user.email')
    phone = serializers.CharField(source='user.phone_number', default="") # Assuming phone on user
    department = serializers.StringRelatedField() # Show dept name
    cgpa = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = ['id', 'name', 'email', 'phone', 'roll_number', 'department', 'batch_year', 'cgpa']

    def get_cgpa(self, obj):
        # Fetch UG score
        edu = Education.objects.filter(student=obj, level='UG').first()
        return edu.score if edu else "N/A"

class ApplicationSerializer(serializers.ModelSerializer):
    student = StudentDetailSerializer(read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)

    class Meta:
        model = Application
        fields = '__all__'