# erp/models.py - MINIMAL NAAC/NIRF Schema (8 Tables + NIRF Fields)
from django.db import models
from profiles.models import StudentProfile
from academics.models import Department



# ==================== CORE ACADEMIC MODELS ====================


class Course(models.Model):
    """Academic Program (B.Tech CSE, MBA) - NAAC 2.1.1 Intake"""
    course_id = models.CharField(max_length=36, primary_key=True)
    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='erp_courses')
    duration_years = models.PositiveSmallIntegerField(default=4)
    total_credits = models.PositiveIntegerField(default=160)
    intake_capacity = models.PositiveIntegerField(default=60)  # NAAC 2.1.1
    is_active = models.BooleanField(default=True)
    
    # ========== NIRF TLR FIELD ADDED ==========
    programme_type = models.CharField(
        max_length=20, null=True, blank=True, 
        choices=[('UG','UG'),('PG','PG'),('PhD','PhD')]
    )
    sanctioned_intake = models.PositiveIntegerField(null=True, blank=True)  # NIRF NT
    # =========================================
    
    class Meta:
        db_table = 'courses'
    
    def __str__(self):
        return f"{self.course_code} - {self.course_name}"



class Subject(models.Model):
    """Individual Subjects - Links enrolment→exams"""
    subject_id = models.CharField(max_length=36, primary_key=True)
    subject_code = models.CharField(max_length=20, unique=True)
    subject_name = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subjects')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='erp_subjects')
    
    semester = models.PositiveSmallIntegerField()
    credits = models.DecimalField(max_digits=3, decimal_places=1, default=4.0)
    max_internal = models.PositiveIntegerField(default=25)
    max_external = models.PositiveIntegerField(default=75)
    total_marks = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'subjects'
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'department', 'subject_code', 'semester'], 
                name='unique_subject_course_dept_sem'
            )
        ]
        ordering = ['department__code', 'semester', 'subject_code']
    
    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"



class StudentSubjectEnrollment(models.Model):
    """CRITICAL: Student Enrolment - NAAC 2.1.1 Demand Ratio"""
    enrollment_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='enrollments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='enrolled_students')
    enrollment_semester = models.PositiveSmallIntegerField()
    batch_year = models.IntegerField()
    enrollment_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'student_subject_enrollments'
        unique_together = ['student', 'subject', 'enrollment_semester']
        ordering = ['-enrollment_date']
    
    def __str__(self):
        return f"{self.student.roll_number} → {self.subject.subject_code}"



# ==================== EXAMS & RESULTS ====================


class Exam(models.Model):
    """Exam Types - Links subjects→marks"""
    exam_id = models.AutoField(primary_key=True)
    exam_code = models.CharField(max_length=20, unique=True)
    exam_name = models.CharField(max_length=100)
    exam_type = models.CharField(max_length=20, choices=[
        ('INTERNAL', 'Internal'),
        ('EXTERNAL', 'External'),
        ('SUPPLEMENTARY', 'Supplementary')
    ])
    max_marks = models.PositiveIntegerField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exams')
    semester = models.PositiveSmallIntegerField()
    exam_date = models.DateField()
    
    class Meta:
        db_table = 'exams'
        ordering = ['exam_date']
    
    def __str__(self):
        return f"{self.exam_code} - {self.subject.subject_code}"



class MarksGrades(models.Model):
    """CRITICAL: Results - NAAC 2.4.1 Pass % (25 Marks!)"""
    marks_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='erp_marks')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='student_marks')
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2)
    grade = models.CharField(max_length=5, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_passed = models.BooleanField(default=False)
    entered_date = models.DateField(auto_now_add=True)
    
    # ========== NIRF GO FIELDS ADDED ==========
    academic_year = models.CharField(max_length=20, null=True, blank=True)  # "2023-24"
    cgpa_equivalent = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)  # 8.75
    # =========================================
    
    class Meta:
        db_table = 'marks_grades'
        unique_together = ['student', 'exam']
        ordering = ['-entered_date']
    
    def __str__(self):
        return f"{self.student.roll_number} - {self.exam.exam_code}"



# ==================== PLACEMENTS ====================


class PlacementRecords(models.Model):
    """CRITICAL: Placements - NAAC 5.2.2 (30 Marks!)"""
    record_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='erp_placements')
    company_name = models.CharField(max_length=255)
    job_role = models.CharField(max_length=255)
    ctc_offered = models.DecimalField(max_digits=10, decimal_places=2)
    offer_letter_date = models.DateField(null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('SELECTED', 'Selected'),
        ('OFFER_ACCEPTED', 'Offer Accepted'),
        ('JOINED', 'Joined'),
        ('REJECTED', 'Rejected')
    ])
    
    # ========== NIRF GO FIELDS ADDED ==========
    median_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # NIRF B15
    programme_level = models.CharField(max_length=20, null=True, blank=True)  # UG/PG/PhD
    # =========================================
    
    class Meta:
        db_table = 'placement_records'
        ordering = ['-offer_letter_date']
    
    def __str__(self):
        return f"{self.student.roll_number} - {self.company_name}"



class PlacementStats(models.Model):
    """Placement Analytics - NAAC 5.2.2"""
    stat_id = models.AutoField(primary_key=True)
    batch_year = models.IntegerField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='placement_stats')
    
    total_students = models.PositiveIntegerField()
    placed_students = models.PositiveIntegerField()
    placement_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    avg_ctc = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    highest_ctc = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    class Meta:
        db_table = 'placement_stats'
        unique_together = ['batch_year', 'department']
    
    def __str__(self):
        return f"{self.department.code}-{self.batch_year}: {self.placement_percentage}%"



class AlumniMaster(models.Model):
    """CRITICAL: Alumni - NAAC 5.3.3 (10 Marks!)"""
    alumni_id = models.AutoField(primary_key=True)
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE, related_name='alumni_record')
    graduation_year = models.IntegerField()
    current_organization = models.CharField(max_length=255, blank=True)
    current_designation = models.CharField(max_length=255, blank=True)
    current_ctc = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    contact_email = models.EmailField(blank=True)
    is_active_alumni = models.BooleanField(default=True)
    
    # ========== NIRF GO FIELDS ADDED ==========
    higher_studies = models.CharField(max_length=255, null=True, blank=True)  # "M.Tech IIT Delhi"
    alumni_feedback_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)  # 4.2/5
    # =========================================
    
    class Meta:
        db_table = 'alumni_master'
        ordering = ['-graduation_year']
    
    def __str__(self):
        return f"{self.student.roll_number} - {self.graduation_year}"



# erp/models.py - ADD THESE 3 FINAL TABLES

# 1. FINANCIAL RESOURCES (TLR 15% BLOCKER)
class NirfFinancials(models.Model):
    financial_year = models.CharField(max_length=9, unique=True)  # '2023-24'
    capital_expenditure_lakhs = models.DecimalField(max_digits=12, decimal_places=2)  # NIRF B18 ⭐
    salary_expenditure_lakhs = models.DecimalField(max_digits=12, decimal_places=2)    # NIRF B19 ⭐
    total_students = models.PositiveIntegerField()
    total_faculty = models.PositiveIntegerField()
    
    class Meta:
        db_table = 'nirf_financials'

# 2. DIVERSITY METRICS (OI 10% BLOCKER)
class NirfDiversity(models.Model):
    category = models.CharField(max_length=20)  # 'sc_st', 'differently_abled', 'sports'
    count_ug = models.PositiveIntegerField()
    count_pg = models.PositiveIntegerField()
    count_phd = models.PositiveIntegerField()
    academic_year = models.CharField(max_length=9)
    
    class Meta:
        db_table = 'nirf_diversity'

# 3. PERCEPTION SURVEYS (PR 10%)
class NirfPerception(models.Model):
    nirf_year = models.IntegerField()
    employer_score = models.DecimalField(max_digits=5, decimal_places=2)  # 0-100
    academic_peer_score = models.DecimalField(max_digits=5, decimal_places=2)
    survey_responses = models.PositiveIntegerField()
    
    class Meta:
        db_table = 'nirf_perception'
