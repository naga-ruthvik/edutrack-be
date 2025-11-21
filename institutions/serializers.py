from rest_framework import serializers
from django.db import transaction
from .models import Institution
from users.models import Profile

class InstitutionCreateSerializer(serializers.ModelSerializer):
    """
    serilaizer to create a new institution
    """
    class Meta:
        model=Institution
        fields=['name','logo','country','state','city','pincode','contact','street']

class ProfileSerializer(serializers.ModelSerializer):
    """
    serilaizer for profile table
    """
    class Meta:
        model=Profile
        fields=('first_name','last_name','role')

class ProfileUploadSerializer(serializers.Serializer):
    """
    Serializer to validate the input fields for the bulk profile creation view.
    It ONLY describes the request body (File, Role, Code), not the DB models.
    """
    file = serializers.FileField(
        required=True,
        help_text="The Excel file containing student data."
    )
    role = serializers.CharField(
        max_length=50,
        help_text="The role for the new profiles (e.g., 'STUDENT')."
    )
    body = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="College Code or any other body identifier."
    )

    # Optional: Add validation to ensure the file type is correct
    def validate_file(self, value):
        filename = value.name.lower()
        if not (filename.endswith('.xlsx') or filename.endswith('.xls') or filename.endswith('.csv')):
            raise serializers.ValidationError("Only Excel files (.xlsx or .xls) are supported.")
        return value
        