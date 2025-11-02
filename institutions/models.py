from django.db import models
from django.contrib.auth.models import AbstractUser

class Institution(models.Model):
    name=models.CharField(max_length=200, unique=True)
    logo=models.ImageField(upload_to='institution_logos/', null=True, blank=True)
    country=models.CharField(max_length=100, null=True, blank=True)
    state=models.CharField(max_length=100, null=True, blank=True)
    city=models.CharField(max_length=200, null=True, blank=True)
    pincode=models.CharField(max_length=100, null=True, blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    contact=models.CharField(max_length=20)
    street=models.TextField()

    def __str__(self):
        return self.name

class Department(models.Model):
    name=models.CharField(max_length=200)
    institution=models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='departments')
    description=models.TextField(null=True, blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together=('name', 'institution')

    def __str__(self):
        return f"{self.name}-{self.institution.name}"