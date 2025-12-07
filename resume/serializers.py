from rest_framework import serializers
from .models import Resume

class ResumeSerializer(serializers.ModelSerializer):
    id=serializers.IntegerField(read_only=True)
    class Meta:
        model = Resume
        fields = ('id','title','job_description','template_style')

class UpdateResumeSerializer(serializers.ModelSerializer):
    id=serializers.IntegerField(read_only=True)
    class Meta:
        model = Resume
        fields = ('id','tailored_content','template_style')
