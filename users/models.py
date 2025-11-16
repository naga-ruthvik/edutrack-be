from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User, PermissionsMixin

class Profile(models.Model):
    """
    Core Profile model. Handles ALL USER DATA.
    """
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        FACULTY = 'FACULTY', 'Faculty'
        HOD = 'HOD', 'Head of Department'
        ADMIN = 'ADMIN', 'Institution Admin'
        
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    institution = models.ForeignKey(
        'institutions.Institution', 
        on_delete=models.PROTECT # Don't delete an institution if users are in it
    )
    department = models.ForeignKey(
        'institutions.Department', 
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    identifier=models.CharField(max_length=50) # roll number - student, faculty_id - mentor a unique id which is given in a college

    class Meta:
        unique_together=('identifier', 'institution','department')

    def __str__(self):
        return self.user.email