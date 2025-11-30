from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom User Model. Handles Login and Authorization Roles.
    """
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"       # Principal / System Admin
        STUDENT = "STUDENT", "Student"
        FACULTY = "FACULTY", "Faculty" 

    # TRAFFIC COP: This field tells us which Profile table to check
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.STUDENT)
    
    # Common fields
    email = models.EmailField(unique=True) 
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True)

    # Djoser Recommendation: Use email as the login field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'role']

    # Fix for clashing related_names
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='authentication_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='authentication_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return self.email