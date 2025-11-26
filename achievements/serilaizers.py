from rest_framework import serializers
from .models import Certificate



from rest_framework import serializers
from .models import Certificate, Skill

class CertificateUploadSerializer(serializers.ModelSerializer):
    # We map this to the model field 'file_url'. DRF handles the conversion.
    file_url = serializers.FileField(required=True)

    # 2. Skills Input: List of Strings (Names)
    skills = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=True
    )

    class Meta:
        model = Certificate
        fields = [
            'id', 
            'title', 
            'issuing_organization', 
            'file_url', # This accepts the file AND returns the S3 URL in response
            'skills', 
            'status',
            'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']

    def validate_skills(self, value):
        """
        Strict Validation: Ensure every skill provided actually exists.
        """
        # Convert input list to lowercase for comparison
        input_skills = [s.lower().strip() for s in value]
        
        # Query DB for these skills
        existing_skills = Skill.objects.filter(name__in=input_skills)
        existing_skills_count = existing_skills.count()

        if existing_skills_count != len(input_skills):
            # Find which one is missing to give a helpful error
            existing_names = set(s.name for s in existing_skills)
            missing = set(input_skills) - existing_names
            raise serializers.ValidationError(
                f"Invalid skills selected: {', '.join(missing)}. Please select from the list."
            )
        
        return value

    def create(self, validated_data):
        # 1. Pop skills list (we handle M2M manually)
        skills_names = validated_data.pop('skills')
        
        # 2. Create Certificate
        # DJANGO MAGIC: Passing the file object to 'file_url' here triggers 
        # the S3 upload via django-storages.
        certificate = Certificate.objects.create(**validated_data)

        # 3. Link Skills (Bulk efficient approach)
        # We already validated they exist, so we can just fetch and add.
        skills_to_add = Skill.objects.filter(name__in=[s.lower().strip() for s in skills_names])
        certificate.claimed_skills.add(*skills_to_add)

        return certificate