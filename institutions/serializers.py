from rest_framework import serializers
from django.db import transaction
from .models import Institution

class InstitutionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model=Institution
        fields=['name','logo','country','state','city','pincode','contact','street']
    