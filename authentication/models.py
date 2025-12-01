from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STUDENT = "STUDENT", "Student"
        FACULTY = "FACULTY", "Faculty"

    role = models.CharField(max_length=50, choices=Role.choices, default=Role.STUDENT)

    # Unique email + additional fields
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True)

    # LOGIN FIELD = USERNAME
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'role']

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='authentication_user_set',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='authentication_user_set',
        blank=True
    )

    def __str__(self):
        return self.username
