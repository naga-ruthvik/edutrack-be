import os
import uuid
from django.db import models
from django.db import connection

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

    # NAAC/NIRF Categories
    class Category(models.TextChoices):
        SPORTS = 'SPORTS', 'Sports'
        CULTURAL = 'CULTURAL', 'Cultural'
        EXTENSION = 'EXTENSION', 'Extension / Outreach (NSS/NCC)'
        MOOC = 'MOOC', 'MOOC / Online Course'
        INTERNSHIP = 'INTERNSHIP', 'Internship'
        PROJECT = 'PROJECT', 'Project / Field Work'
        TECHNICAL = 'TECHNICAL', 'Technical / Hackathon'
        RESEARCH = 'RESEARCH', 'Research Paper / Patent'
        OTHER = 'OTHER', 'Other'

    class Level(models.TextChoices):
        COLLEGE = 'COLLEGE', 'College / Inter-Collegiate'
        STATE = 'STATE', 'State / University'
        NATIONAL = 'NATIONAL', 'National'
        INTERNATIONAL = 'INTERNATIONAL', 'International'

    class Rank(models.TextChoices):
        PARTICIPATION = 'PARTICIPATION', 'Participation'
        FIRST = 'FIRST', 'First Prize / Gold'
        SECOND = 'SECOND', 'Second Prize / Silver'
        THIRD = 'THIRD', 'Third Prize / Bronze'
        WINNER = 'WINNER', 'Winner'

    # --- RELATIONS ---
    student = models.ForeignKey(
        'profiles.StudentProfile', 
        on_delete=models.CASCADE, 
        related_name='achievements'
    )

    # 1. PRIMARY SKILL (User Input)
    # The student selects just ONE skill from the dropdown. 
    # This keeps the UI simple and gives you a definite category.
    primary_skill = models.ForeignKey(
        Skill,
        on_delete=models.PROTECT,
        related_name='primary_achievements',
        help_text="The main skill this certificate validates.",
        null=True,
        blank=True
    )

    # 2. SECONDARY SKILLS (AI Enriched)
    # Hidden from the upload form. Populated by AI analysis.
    secondary_skills = models.ManyToManyField(
        Skill,
        related_name='secondary_achievements',
        blank=True
    )

    # --- CORE DATA ---
    title = models.CharField(max_length=255)
    issuing_organization = models.CharField(max_length=255)
    file_url = models.FileField(
        upload_to=certificate_upload_path,
        max_length=255
    )
    verification_url = models.URLField(
        null=True, 
        blank=True, 
        help_text="Public URL to verify credentials (e.g. Coursera/Credly link)"
    )

    # --- REPORTING METADATA (Filled by AI or Student) ---
    category = models.CharField(max_length=50, choices=Category.choices, blank=True)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.COLLEGE)
    rank = models.CharField(max_length=20, choices=Rank.choices, default=Rank.PARTICIPATION)
    
    date_of_event = models.DateField(help_text="Date mentioned on certificate", blank=True, null=True)
    academic_year = models.CharField(max_length=10, blank=True, help_text="Auto-generated (e.g. 2023-24)")

    # --- AI CONTEXT & SCORING ---
    # A rich summary written by the AI for your Chatbot/RAG system.
    ai_summary = models.TextField(blank=True, help_text="Short summary for Chatbot context.")
    ocr_text = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    credit_points = models.IntegerField(default=0)
    
    verified_by = models.ForeignKey(
        'profiles.FacultyProfile', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_achievements'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-calculate Academic Year (e.g., June 2023 -> "2023-24")
        if self.date_of_event:
            self.academic_year = self.get_academic_year(self.date_of_event)
        super().save(*args, **kwargs)

    @staticmethod
    def get_academic_year(date_obj):
        # Assumes academic year starts in June (Month 6)
        if date_obj.month >= 6: 
            return f"{date_obj.year}-{str(date_obj.year + 1)[-2:]}"
        else:
            return f"{date_obj.year - 1}-{str(date_obj.year)[-2:]}"

    def __str__(self):
        return f"{self.title} ({self.status})"