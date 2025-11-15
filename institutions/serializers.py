from rest_framework import serializers
from django.db import transaction
from .models import Institution
from users.models import Profile

class InstitutionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model=Institution
        fields=['name','logo','country','state','city','pincode','contact','street']

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model=Profile
        fields=('first_name','last_name','role')