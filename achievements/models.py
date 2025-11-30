import os
import uuid
from django.db import models
from django.db import connection # <--- REQUIRED for Multi-tenancy

def certificate_upload_path(instance, filename):
    """
    Generates the S3 path based on the CURRENT TENANT SCHEMA.
    Format: certificates/<tenant_schema>/student_<id>/<uuid>_<filename>
    """
    # 1. Get the Current Schema Name (e.g., 'vardhaman', 'cbit')
    # Since we are inside the tenant context, this variable holds the current schema.
    schema_name = connection.schema_name
    
    # 2. Get Student ID
    # Note: instance.student is now a StudentProfile, so we use its ID
    student_id = instance.student.id
    
    # 3. Generate Random Filename
    ext = filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4()}.{ext}"
    
    # 4. Construct Path
    return f"certificates/{schema_name}/student_{student_id}/{unique_filename}"


class Skill(models.Model):
    """
    Standardized tags for skills.
    """
    name = models.CharField(max_length=100, unique=True)
    
    def save(self, *args, **kwargs):
        self.name = self.name.lower().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Certificate(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'AI Processing'
        AI_VERIFIED = 'AI_VERIFIED', 'Verified by AI'
        NEEDS_REVIEW = 'NEEDS_REVIEW', 'Sent to Mentor'
        MANUAL_VERIFIED = 'MANUAL_VERIFIED', 'Verified by Mentor'
        REJECTED = 'REJECTED', 'Rejected'

    # 1. CORRECTED RELATION: Points to StudentProfile
    student = models.ForeignKey(
        'profiles.StudentProfile', 
        on_delete=models.CASCADE, 
        related_name='certificates'
    )
    
    title = models.CharField(max_length=255)
    issuing_organization = models.CharField(max_length=255)

    # 2. CORRECTED UPLOAD PATH
    file_url = models.FileField(
        upload_to=certificate_upload_path,
        max_length=255 
    )
    
    # 3. MERGED SKILLS (Simplified as requested)
    # This list starts as what the student claimed. 
    # AI/Mentor can remove/add to this same list during verification.
    skills = models.ManyToManyField(
        Skill, 
        related_name='certificates',
        blank=True
    )

    # --- AI & VERIFICATION DATA ---
    generated_description = models.TextField(blank=True, null=True)
    ocr_text = models.TextField(blank=True, null=True)
    
    # --- STATUS & SCORING ---
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    
    credit_points = models.IntegerField(default=0)
    
    # 4. CORRECTED RELATION: Points to FacultyProfile
    verified_by = models.ForeignKey(
        'profiles.FacultyProfile', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_certificates'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # 5. CORRECTED STRING: Uses roll_number instead of identifier
        return f"{self.title} ({self.student.roll_number})"