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


# ========== NIRF RP TABLES (30% SCORE) - ADDED BELOW ==========

class NirfPublication(models.Model):
    """
    NIRF RP B5-B10: Scopus/WoS Publications (20% score)
    """
    pub_id = models.AutoField(primary_key=True)
    
    # Links to Person (Student/Faculty)
    student = models.ForeignKey(
        'profiles.StudentProfile', 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        related_name='nirf_publications'
    )
    faculty = models.ForeignKey(
        'profiles.FacultyProfile', 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        related_name='nirf_publications'
    )
    
    # NIRF Required Fields
    title = models.CharField(max_length=500)
    journal_name = models.CharField(max_length=255)
    scopus_wos_id = models.CharField(max_length=100, unique=True, null=True, blank=True)  # NIRF validates
    volume_issue = models.CharField(max_length=50, blank=True)  # "Vol 45, Issue 3"
    page_numbers = models.CharField(max_length=50, blank=True)   # "123-145"
    doi_url = models.URLField(blank=True, null=True)
    
    pub_date = models.DateField()
    citations = models.PositiveIntegerField(default=0)
    
    # NIRF Author Position (for student bonus)
    author_position = models.CharField(
        max_length=20, blank=True,
        choices=[('FIRST', 'First'), ('CORRESPONDING', 'Corresponding'), ('CO_AUTHOR', 'Co-Author')]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'nirf_publications'
        indexes = [models.Index(fields=['pub_date', 'scopus_wos_id'])]
    
    def __str__(self):
        return f"{self.title[:50]}... ({self.pub_date.year})"


class NirfResearchProject(models.Model):
    """
    NIRF RP B15-B20: Research Funding (10% score)
    """
    proj_id = models.AutoField(primary_key=True)
    
    # Principal Investigator
    pi_faculty = models.ForeignKey(
        'profiles.FacultyProfile', 
        on_delete=models.CASCADE,
        related_name='nirf_projects'
    )
    
    # NIRF Required Fields
    title = models.CharField(max_length=500)
    funding_agency = models.CharField(max_length=255)  # "DST", "UGC", "Industry"
    amount_lakhs = models.DecimalField(max_digits=12, decimal_places=2)  # Rs. Lakhs
    duration_years = models.PositiveSmallIntegerField()
    start_year = models.IntegerField()  # NIRF: Last 5 years
    end_year = models.IntegerField(null=True, blank=True)
    project_type = models.CharField(
        max_length=20,
        choices=[
            ('MAJOR', 'Major Project'),
            ('MINOR', 'Minor Project'), 
            ('INDUSTRY', 'Industry Sponsored'),
            ('CONSULTANCY', 'Consultancy')
        ]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'nirf_research_projects'
        indexes = [models.Index(fields=['start_year', 'funding_agency'])]
    
    def __str__(self):
        return f"{self.title[:50]}... (₹{self.amount_lakhs}L)"


class NirfPatent(models.Model):
    """
    NIRF RP B25-B30: Patents (5% score)
    """
    patent_id = models.AutoField(primary_key=True)
    
    # Links to Inventor
    student = models.ForeignKey(
        'profiles.StudentProfile', 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        related_name='nirf_patents'
    )
    faculty = models.ForeignKey(
        'profiles.FacultyProfile', 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        related_name='nirf_patents'
    )
    
    # NIRF Required Fields
    title = models.CharField(max_length=500)
    patent_number = models.CharField(max_length=100, unique=True)  # Application/Grant #
    status = models.CharField(
        max_length=20,
        choices=[
            ('FILED', 'Filed'),
            ('PUBLISHED', 'Published'), 
            ('GRANTED', 'Granted')
        ]
    )
    filing_date = models.DateField(null=True, blank=True)
    grant_date = models.DateField(null=True, blank=True)
    inventor_position = models.CharField(
        max_length=20, blank=True,
        choices=[('FIRST', 'First'), ('CO_INVENTOR', 'Co-Inventor')]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'nirf_patents'
        indexes = [models.Index(fields=['status', 'grant_date'])]
    
    def __str__(self):
        return f"{self.title[:50]}... ({self.status})"


class NirfExecDevelopment(models.Model):
    """
    NIRF RP B35: Executive Development Programs (5% score)
    """
    program_id = models.AutoField(primary_key=True)
    
    faculty = models.ForeignKey(
        'profiles.FacultyProfile', 
        on_delete=models.CASCADE,
        related_name='exec_development_programs'
    )
    
    programme_name = models.CharField(max_length=255)
    revenue_lakhs = models.DecimalField(max_digits=12, decimal_places=2)  # Program earnings
    participants = models.PositiveIntegerField()
    duration_days = models.PositiveIntegerField()
    year = models.IntegerField()  # NIRF: Last 3 years
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'nirf_exec_development'
    
    def __str__(self):
        return f"{self.programme_name} (₹{self.revenue_lakhs}L, {self.participants} participants)"
