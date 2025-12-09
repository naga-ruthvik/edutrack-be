from django.db import models
from django.conf import settings


class StudentProfile(models.Model):
    """
    Strict Data for Students only.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    
    # Unique ID within this College Schema
    roll_number = models.CharField(max_length=50, unique=True)
    
    # Link to Academics App
    department = models.ForeignKey(
        'academics.Department', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='students'
    )
    batch_year = models.IntegerField(help_text="e.g. 2024")
    current_semester = models.IntegerField(default=1)

    # Mentorship (Points to Faculty Profile)
    mentor = models.ForeignKey(
        'profiles.FacultyProfile', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='mentees'
    )
    
    # ========== NIRF FIELDS ADDED (100% BACKWARD COMPATIBLE) ==========
    # NIRF OI (10%) + GO (20%) - Diversity & PhD Data
    state = models.CharField(max_length=50, null=True, blank=True)  # e.g. "Telangana"
    category = models.CharField(
        max_length=20, null=True, blank=True, 
        choices=[
            ('GEN', 'General'), 
            ('OBC', 'OBC'), 
            ('SC', 'SC'), 
            ('ST', 'ST')
        ]
    )
    gender = models.CharField(
        max_length=10, null=True, blank=True,
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    )
    differently_abled = models.BooleanField(default=False, null=True, blank=True)
    phd_enrolled = models.BooleanField(default=False, null=True, blank=True)
    # ================================================================

    def __str__(self):
        return f"{self.roll_number} - {self.user.get_full_name()}"


class FacultyProfile(models.Model):
    """
    Strict Data for Faculty only.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='faculty_profile')
    
    employee_id = models.CharField(max_length=50, unique=True)
    
    # Hardcoded Designations (As requested)
    class Designation(models.TextChoices):
        PROFESSOR = 'PROFESSOR', 'Professor'
        ASSOC_PROF = 'ASSOC_PROF', 'Associate Professor'
        ASST_PROF = 'ASST_PROF', 'Assistant Professor'
        LECTURER = 'LECTURER', 'Lecturer'
        LAB_INSTRUCTOR = 'LAB_INSTRUCTOR', 'Lab Instructor'
        PRINCIPAL = 'PRINCIPAL', 'Principal'

    designation = models.CharField(
        max_length=50, 
        choices=Designation.choices, 
        default=Designation.ASST_PROF
    )
    
    department = models.ForeignKey(
        'academics.Department',
        on_delete=models.SET_NULL,
        null=True,
        related_name='faculty'
    )
    
    # Role Flags
    is_hod = models.BooleanField(default=False)
    joining_date = models.DateField(null=True, blank=True)
    
    # ========== NIRF FIELDS ADDED (100% BACKWARD COMPATIBLE) ==========
    # NIRF TLR (30%) + RP (30%) - Faculty Quality Metrics
    phd_qualification = models.BooleanField(default=False)
    years_experience = models.PositiveIntegerField(null=True, blank=True)
    publications_count = models.PositiveIntegerField(default=0)
    # ================================================================

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_designation_display()})"


class Education(models.Model):
    class Level(models.TextChoices):
        SCHOOL_10 = '10', 'Class 10'
        SCHOOL_12 = '12', 'Class 12'
        DIPLOMA = 'DIPLOMA', 'Diploma'
        UNDERGRAD = 'UG', 'Undergraduate'
        POSTGRAD = 'PG', 'Postgraduate'

    # Link to the Student Profile (One-to-Many)
    student = models.ForeignKey(
        'StudentProfile', 
        on_delete=models.CASCADE, 
        related_name='education_history' # Access via: profile.education_history.all()
    )
    
    institution_name = models.CharField(max_length=255) # e.g. "Delhi Public School"
    board_or_university = models.CharField(max_length=255) # e.g. "CBSE", "JNTU"
    level = models.CharField(max_length=20, choices=Level.choices)
    
    # Flexible scoring (CGPA or Percentage)
    score = models.CharField(max_length=20, help_text="e.g. 9.8 CGPA or 88%")
    
    passing_year = models.IntegerField()
    
    # ========== NIRF FIELD ADDED (OPTIONAL) ==========
    # NIRF GO - PhD Award Tracking (if applicable)
    is_phd_awarded = models.BooleanField(default=False, null=True, blank=True)
    # ================================================

    class Meta:
        ordering = ['-passing_year'] # Show latest first

    def __str__(self):
        return f"{self.level} - {self.student.user.get_full_name()}"
