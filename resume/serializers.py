from rest_framework import serializers
from .models import Resume

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ('title','job_description','template_style')

class UpdateResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ('tailored_content','template_style')
