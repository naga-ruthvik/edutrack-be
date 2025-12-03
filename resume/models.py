from django.db import models

# Create your models here.
from django.db import models

class Resume(models.Model):
    class TemplateStyle(models.TextChoices):
        MODERN = 'MODERN', 'Modern (Two Column)'
        CLASSIC = 'CLASSIC', 'Classic (ATS Friendly)'
        CREATIVE = 'CREATIVE', 'Creative'

    # Link to Student
    student = models.ForeignKey(
        'profiles.StudentProfile',
        on_delete=models.CASCADE,
        related_name='resumes'
    )

    # --- 1. TARGETING DATA ---
    # The student provides this to guide the AI
    title = models.CharField(max_length=255, help_text="e.g., 'Google Frontend Application'")
    target_role = models.CharField(max_length=255, help_text="e.g., 'Software Engineer'", null=True, blank=True)
    job_description = models.TextField(
        help_text="Paste the full JD here for AI analysis.", null=True, blank=True
    )

    tailored_content = models.JSONField(
        default=dict, 
        blank=True,
        help_text="The final structured data used to generate the PDF."
    )

    ats_score = models.IntegerField(null=True, blank=True)
    ai_feedback = models.TextField(null=True, blank=True, help_text="Suggestions to improve.")

    template_style = models.CharField(
        max_length=50, 
        choices=TemplateStyle.choices, 
        default=TemplateStyle.CLASSIC
    )
    
    file_url = models.FileField(upload_to='resumes/', null=True, blank=True)

    def __str__(self):
        return f"{self.student.first_name} - {self.title}"