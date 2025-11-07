from rest_framework import serializers
from .models import User, Profile

# serializer for models
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model=Profile
        fields=('name')