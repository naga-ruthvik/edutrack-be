# serializer for models
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from rest_framework import serializers
from django.db import transaction
from institutions.models import Institution
from institutions.serializers import InstitutionCreateSerializer
from .models import User, Profile

class InstitutionAdminCreateSerializer(BaseUserCreateSerializer):
    first_name = serializers.CharField(write_only=True, required=True)
    last_name = serializers.CharField(write_only=True, required=True)
    institution = InstitutionCreateSerializer(write_only=True)

    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = (
            'email', 
            'username',
            'password', 
            'first_name', 
            'last_name', 
            'institution'
        )
        extra_kwargs = {
            'username': {'required': False, 'allow_blank': True}
        }

    def validate(self, attrs):
        # 1. Pop all custom fields *before* calling super().validate().
        # We store them on 'self' to use in the 'create' method.
        self.institution_data = attrs.pop('institution')
        self.first_name = attrs.pop('first_name')
        self.last_name = attrs.pop('last_name')

        # 2. Handle the username logic
        if 'username' not in attrs or not attrs['username']:
            attrs['username'] = attrs['email']
        
        # 3. Call super().validate() with *only* the user fields.
        validated_data = super().validate(attrs)
        
        return validated_data

    @transaction.atomic
    def create(self, validated_data):
        # 'validated_data' now *only* contains the User fields
        # because our 'validate' method cleaned it.
        
        # 1. Call the parent's create() method with the clean data.
        # This will correctly create the User and hash the password.
        user = super().create(validated_data) 

        # 2. Create the new Institution using the data we saved on 'self'
        institution = Institution.objects.create(**self.institution_data)
        # 3. Create the Admin's Profile using data from 'self'
        Profile.objects.create(
            user=user,
            first_name=self.first_name,
            last_name=self.last_name,
            institution=institution,
            role=Profile.Role.ADMIN
        )
        return user

class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
        extra_kwargs={
            'password':{
                'write_only':True
            }
        }