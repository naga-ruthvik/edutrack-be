from django.db import models
from django.contrib.auth.models import AbstractUser


class Department(models.Model):
    name = models.CharField(max_length=100,unique=True)       # e.g., "Computer Science"
    code = models.CharField(max_length=20, unique=True)        # e.g., "CSE"
    
    # We link head to Faculty via string to avoid circular imports
    head = models.OneToOneField(
        'profiles.FacultyProfile',                   
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='headed_department'
    )

    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name
    