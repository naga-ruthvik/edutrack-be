from django.db import models
from authentication.models import User

# Create your models here.

class Organization(models.Model):
    name = models.CharField(max_length=255)
    logo_url = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False) # For the "Green Tick"
    
    # ATS INTEGRATION FIELDS
    ats_provider = models.CharField(max_length=50, default='none') # e.g., "Workday", "Greenhouse"
    knit_integration_id = models.CharField(max_length=100, blank=True) # The ID from GetKnit

    def __str__(self):
        return self.name

class RecruiterProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        MANAGER = 'MANAGER', 'Hiring Manager'

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    company = models.CharField(max_length=100) # Kept for legacy/display if needed, but redundant with organization link
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='recruiter_profile')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    designation = models.CharField(max_length=100)
    
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MANAGER)

    def __str__(self):
        return f"{self.name} - {self.organization.name}"

class JobPosting(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        CLOSED = 'CLOSED', 'Closed'

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=100, blank=True)
    salary_range = models.CharField(max_length=100, blank=True)
    
    min_cgpa = models.DecimalField(max_digits=4, decimal_places=2) # e.g. 7.50
    target_batches = models.JSONField(default=list) # e.g. [2025, 2026]
    target_colleges = models.JSONField(default=list) # e.g. ["IIT Delhi", "BITS Pilani"]
    required_skills = models.JSONField(default=list) # e.g. ["Python", "Django"]
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    
    ats_job_id = models.CharField(max_length=100, blank=True) # The ID inside Workday/Greenhouse

    def __str__(self):
        return f"{self.title} at {self.organization.name}"

class Application(models.Model):
    class SyncStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SYNCING = 'SYNCING', 'Syncing'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'

    class InternalStatus(models.TextChoices):
        APPLIED = 'APPLIED', 'Applied'
        SHORTLISTED = 'SHORTLISTED', 'Shortlisted'
        INTERVIEW = 'INTERVIEW', 'Interview'
        OFFERED = 'OFFERED', 'Offered'
        REJECTED = 'REJECTED', 'Rejected'

    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    # Use string reference to avoid circular import issues if any
    student = models.ForeignKey('profiles.StudentProfile', on_delete=models.CASCADE, related_name='applications')
    
    status = models.CharField(max_length=20, choices=InternalStatus.choices, default=InternalStatus.APPLIED)
    
    # ATS Sync Data
    sync_status = models.CharField(max_length=20, choices=SyncStatus.choices, default=SyncStatus.PENDING)
    external_candidate_id = models.CharField(max_length=100, blank=True)
    
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} -> {self.job.title}"