from rest_framework import serializers
from .models import Certificate, Skill

class CertificateUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ["file_url"]

    def create(self, validated_data):
        certificate = Certificate.objects.create(**validated_data)
        return certificate

class CertificateListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ["id", "file_url", "verification_url", "secondary_skills","status", "title", "issuing_organization", "category", "level", "rank", "ai_summary"]

class CertificateVerificationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        ('MANUAL_VERIFIED', 'Verified by Mentor'),
        ('REJECTED', 'Rejected')
    ])
