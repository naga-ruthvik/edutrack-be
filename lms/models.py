import uuid
from django.db import models
from django.conf import settings  # Your Custom User

# SAFE IMPORTS - Won't break if models don't exist yet
try:
    from academics.models import Department
except ImportError:
    Department = None

try:
    from profiles.models import StudentProfile, FacultyProfile
except ImportError:
    StudentProfile = None
    FacultyProfile = None

# =============================================================================
# 1. TENANT TABLES (Inside each institution schema: vardhaman, cbit, etc.)
# =============================================================================

class Session(models.Model):
    """
    Academic Year/Term - Edlink: GET /api/v2/graph/sessions
    e.g. "AY 2024-25", "Semester 1 2024"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)  # "AY 2024-25"
    start_date = models.DateField()
    end_date = models.DateField()
    state = models.CharField(max_length=20, default='active')  # active/inactive
    type = models.CharField(max_length=20, default='semester')  # semester/annual
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['name', 'start_date']
        indexes = [
            models.Index(fields=['state', 'start_date']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.type})"

class Course(models.Model):
    """
    Program/Paper - Edlink: GET /api/v2/graph/courses
    e.g. "Data Structures & Algorithms", "CS425"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)  # "CS425", "MATH101"
    
    # Link to YOUR existing Department (manual mapping by admin)
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='lms_courses',
        help_text="Map to your local department structure"
    )
    
    # Link to Session (nullable - some courses span multiple)
    session = models.ForeignKey(
        Session, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='courses'
    )
    
    # Edlink timestamps
    created_date = models.DateTimeField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['code', 'department']
        indexes = [
            models.Index(fields=['department', 'session']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"{self.code or 'N/A'} - {self.name}"

class LmsClass(models.Model):
    """
    Class/Section Offering - Edlink: GET /api/v2/graph/classes
    e.g. "DS-A", "Math101-Sec1" (actual taught section)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)  # "Section A", "Batch 2024"
    state = models.CharField(max_length=20, default='active')  # active/upcoming
    
    # Links to parent Course
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='classes'
    )
    
    # Edlink sends array of session UUIDs
    session_ids = models.JSONField(default=list)  # ["uuid1", "uuid2"]
    
    # From Edlink: references.enrollments (quick count)
    enrollment_count = models.PositiveIntegerField(default=0)
    
    # Edlink timestamps
    created_date = models.DateTimeField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['course', 'name']
        indexes = [
            models.Index(fields=['course', 'state']),
            models.Index(fields=['enrollment_count']),
        ]
    
    def __str__(self):
        return f"{self.course.code} - {self.name} ({self.enrollment_count} students)"

class LmsPerson(models.Model):
    """
    Raw LMS Person Data - Edlink: GET /api/v2/graph/people (READ-ONLY)
    Auto-links to YOUR User via email match
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Exact match to YOUR User fields
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=255)
    email = models.EmailField(db_index=True)  # ← MATCHES YOUR User.email!
    
    # LMS-specific roles (may differ from your User.role)
    roles = models.JSONField(default=list)  # ["student"], ["teacher", "admin"]
    
    # Direct link to YOUR Custom User (admin creates, sync auto-links)
    django_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lms_person'  # user.lms_person
    )
    
    # Edlink audit timestamps
    created_date = models.DateTimeField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['email']),  # Fast User lookup
            models.Index(fields=['roles']),
        ]
    
    def __str__(self):
        return self.display_name

class PersonIdentifier(models.Model):
    """
    Extra IDs from LMS - Edlink: person["identifiers"][]
    e.g. {"type": "canvas_id", "value": "123"}
    """
    person = models.ForeignKey(
        LmsPerson, 
        on_delete=models.CASCADE, 
        related_name='identifiers'
    )
    type = models.CharField(max_length=50, db_index=True)  # "canvas_id", "sis_id"
    value = models.CharField(max_length=255, db_index=True)
    
    class Meta:
        unique_together = ['person', 'type']
        indexes = [
            models.Index(fields=['type', 'value']),
        ]
    
    def __str__(self):
        return f"{self.person.display_name} - {self.type}:{self.value}"

class Enrollment(models.Model):
    """
    MAGIC LINK: Person + Class + Grades - Edlink: GET /api/v2/graph/enrollments
    NAAC powerhouse for student strength & faculty workload
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    person = models.ForeignKey(
        LmsPerson, 
        on_delete=models.CASCADE, 
        related_name='enrollments'
    )
    class_section = models.ForeignKey(
        LmsClass, 
        on_delete=models.CASCADE, 
        related_name='enrollments'
    )
    
    role = models.CharField(max_length=20, db_index=True)  # "student", "teacher"
    state = models.CharField(max_length=20, default='active')  # active/completed
    
    # FINAL COURSE GRADES (NAAC GOLD!)
    final_letter_grade = models.CharField(max_length=10, null=True, blank=True)  # "A", "B+"
    final_numeric_grade = models.DecimalField(
        max_digits=5, decimal_places=2, 
        null=True, blank=True  # 8.75 CGPA, 85.50%
    )
    
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Edlink timestamps
    created_date = models.DateTimeField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['person', 'class_section', 'role']
        indexes = [
            models.Index(fields=['role', 'state']),
            models.Index(fields=['class_section', 'role']),
            models.Index(fields=['final_numeric_grade']),
        ]
    
    def __str__(self):
        return f"{self.person.display_name} ({self.role}) in {self.class_section}"

class Assignment(models.Model):
    """
    Quiz/Homework/Test - Edlink: GET /api/v2/graph/classes/{id}/assignments
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class_section = models.ForeignKey(
        LmsClass, 
        on_delete=models.CASCADE, 
        related_name='assignments'
    )
    
    title = models.CharField(max_length=255)
    state = models.CharField(max_length=20, default='open')  # open/locked
    
    due_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    points_possible = models.DecimalField(max_digits=10, decimal_places=2)
    grading_type = models.CharField(max_length=50, default='points')  # points/percent
    
    created_date = models.DateTimeField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['class_section', 'due_date']),
            models.Index(fields=['state']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.class_section}) - {self.points_possible} pts"

class Submission(models.Model):
    """
    Student work + marks - Edlink: GET /api/v2/graph/.../submissions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    assignment = models.ForeignKey(
        Assignment, 
        on_delete=models.CASCADE, 
        related_name='submissions'
    )
    student = models.ForeignKey(
        LmsPerson, 
        on_delete=models.CASCADE, 
        related_name='submissions'
    )
    
    submitted_at = models.DateTimeField(null=True, blank=True)
    grade_points = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True
    )
    override_due_date = models.DateTimeField(null=True, blank=True)
    
    created_date = models.DateTimeField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['assignment', 'student']
        indexes = [
            models.Index(fields=['student', 'submitted_at']),
            models.Index(fields=['grade_points']),
        ]
    
    def __str__(self):
        return f"{self.student.display_name} - {self.assignment.title}"