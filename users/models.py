from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User, PermissionsMixin
from django.db.models import Q

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
    identifier=models.CharField(max_length=50, null=True, blank=True) # roll number - student, faculty_id - mentor a unique id which is given in a college
    mentor = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='mentees', # Access students via: faculty_profile.mentees.all()
        limit_choices_to={'role__in': ['FACULTY', 'HOD']}
    )

    class Meta:
        # Remove unique_together
        # unique_together=('identifier', 'institution') 

        # Add this instead:
        constraints = [
            models.UniqueConstraint(
                fields=['identifier', 'institution'],
                name='unique_identifier_per_institution',
                # 2. The Magic Condition:
                # Only enforce uniqueness if 'identifier' is NOT null and NOT empty
                condition=Q(identifier__isnull=False) & ~Q(identifier='')
            )
        ]

    def __str__(self):
        return self.user.email