from rest_framework import serializers
from .models import Certificate
import json


from rest_framework import serializers
from .models import Certificate, Skill

class CertificateUploadSerializer(serializers.ModelSerializer):
    skills = serializers.CharField(write_only=True)

    class Meta:
        model = Certificate
        fields = ["title","file_url", "verification_url", "skills"]

    def validate_skills(self, value):
        import json

        # Case 1: ['["python"]']
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
            value = value[0]

        # Case 2: "['python']"
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except:
                raise serializers.ValidationError("Invalid JSON format for skills")

        if not isinstance(value, list):
            raise serializers.ValidationError("Skills must be a list")

        # Normalize
        value = [s.lower().strip() for s in value]

        # DB validation
        print("value",value)
        existing = Skill.objects.filter(name__in=value)
        print("existing:",existing)
        if existing.count() != len(value):
            missing = set(value) - set(s.name for s in existing)
            raise serializers.ValidationError(f"Invalid skills: {', '.join(missing)}")

        return value

    def validate(self, attrs):
        # Move validated skills into validated_data
        if "skills" in self.initial_data:
            attrs["skills"] = self.validate_skills(self.initial_data["skills"])
        return attrs

    def create(self, validated_data):
        skills_names = validated_data.pop("skills")
        certificate = Certificate.objects.create(**validated_data)
        skills_to_add = Skill.objects.filter(name__in=skills_names)
        certificate.secondary_skills.add(*skills_to_add)
        return certificate
