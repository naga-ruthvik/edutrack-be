from rest_framework import serializers
from .models import Certificate, Skill

class CertificateUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ["file_url"]

    def create(self, validated_data):
        # Set default values for required fields that aren't in the input
        validated_data['title'] = validated_data.get('title', 'Processing...')
        validated_data['issuing_organization'] = validated_data.get('issuing_organization', 'Processing...')
        
        certificate = Certificate.objects.create(**validated_data)
        return certificate

class CertificateListSerializer(serializers.ModelSerializer):
    secondary_skills = serializers.StringRelatedField(many=True)
    student=serializers.StringRelatedField(read_only=True)
    class Meta:
        model = Certificate
        fields = ["id", "file_url", "verification_url", "secondary_skills","status", "title", "issuing_organization", "category", "level", "rank", "ai_summary", "student"]

class CertificateVerificationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        ('MANUAL_VERIFIED', 'Verified by Mentor'),
        ('REJECTED', 'Rejected')
    ])
