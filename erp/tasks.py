# erp/tasks.py
import requests
from celery import shared_task, chain
from django_tenants.utils import schema_context
from datetime import datetime
from authentication.models import User
from academics.models import Department
from profiles.models import StudentProfile, FacultyProfile
from .models import (
    Course,
    Subject,
    StudentSubjectEnrollment,
    Exam,
    MarksGrades,
    PlacementRecords,
    PlacementStats,
    AlumniMaster,
)

ERP_BASE_URL = "https://backend-erp-zeta.vercel.app/api"


def get_headers():
    return {"Content-Type": "application/json"}

def parse_iso_date(date_str):
    if not date_str:
        return None
    # "2015-01-15T00:00:00.000Z" -> "2015-01-15"
    return date_str.split("T")[0]


def fetch_erp(endpoint: str):
    url = f"{ERP_BASE_URL}/{endpoint}"
    resp = requests.get(url, headers=get_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        return data.get("data", [])
    return []


@shared_task
def sync_users(schema_name: str):
    with schema_context(schema_name):
        data = fetch_erp("users")
        synced = 0
        for item in data:
            User.objects.update_or_create(
                username=item["username"],
                defaults={
                    "email": item.get("email", ""),
                    "first_name": item.get("first_name", "") or "",
                    "last_name": item.get("last_name", "") or "",
                    "is_staff": bool(item.get("is_staff", 0)),
                    "is_active": bool(item.get("is_active", 1)),
                },
            )
            synced += 1
        print(f"{schema_name}: {synced} users")
        return {"synced": synced}


@shared_task
def sync_departments(schema_name: str):
    with schema_context(schema_name):
        data = fetch_erp("departments")
        synced = 0
        for item in data:
            Department.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                },
            )
            synced += 1
        print(f"{schema_name}: {synced} departments")
        return {"synced": synced}

@shared_task
def sync_faculty(schema_name: str):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    with schema_context(schema_name):
        data = fetch_erp("faculty")
        synced = 0
        for item in data:
            username = item["employee_id"]  # or whatever mapping you decided
            email = item.get("email") or f"{username}@noemail.com"

            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "email": email,
                    "is_active": True,
                },
            )

            dept = None
            dep_code = item.get("department_code")
            if dep_code:
                dept = Department.objects.filter(code=dep_code).first()

            FacultyProfile.objects.update_or_create(
                employee_id=item["employee_id"],
                defaults={
                    "user": user,
                    "designation": item.get("designation", "ASST_PROF"),
                    "department": dept,
                    "is_hod": bool(item.get("is_hod", 0)),
                    "joining_date": parse_iso_date(item.get("joining_date")),
                },
            )
            synced += 1

        print(f"{schema_name}: {synced} faculty")
        return {"synced": synced}




@shared_task
def sync_students(schema_name: str):
    with schema_context(schema_name):
        data = fetch_erp("students")
        synced = 0
        for item in data:
            roll = item["roll_number"]
            email = item.get("email") or f"{roll}@noemail.com"

            # 1) Try to find by email first (avoid duplicate email)
            user = User.objects.filter(email=email).first()

            if user is None:
                # 2) If no one with that email, create/update by username
                user, _ = User.objects.update_or_create(
                    username=roll,
                    defaults={
                        "email": email,
                        "is_active": True,
                    },
                )

            # Department
            dept = None
            dep_code = item.get("department_code")
            if dep_code:
                dept = Department.objects.filter(code=dep_code).first()

            # Mentor
            mentor = None
            mentor_emp = item.get("mentor_employee_id")
            if mentor_emp:
                mentor = FacultyProfile.objects.filter(
                    employee_id=mentor_emp
                ).first()

            StudentProfile.objects.update_or_create(
                roll_number=roll,
                defaults={
                    "user": user,
                    "department": dept,
                    "batch_year": item["batch_year"],
                    "current_semester": item.get("current_semester", 1),
                    "mentor": mentor,
                },
            )
            synced += 1

        print(f"{schema_name}: {synced} students")
        return {"synced": synced}

@shared_task
def sync_courses(schema_name: str):
    with schema_context(schema_name):
        data = fetch_erp("courses")
        synced = 0
        for item in data:
            dept = None
            dep_code = item.get("department_code")
            if dep_code:
                dept = Department.objects.filter(code=dep_code).first()

            Course.objects.update_or_create(
                course_id=item["course_id"],
                defaults={
                    "course_code": item["course_code"],
                    "course_name": item["course_name"],
                    "department": dept,
                    "duration_years": item.get("duration_years", 4),
                    "total_credits": item.get("total_credits", 160),
                    "intake_capacity": item.get("intake_capacity", 60),
                    "is_active": bool(item.get("is_active", 1)),
                },
            )
            synced += 1
        print(f"{schema_name}: {synced} courses")
        return {"synced": synced}

@shared_task
def sync_subjects(schema_name: str):
    with schema_context(schema_name):
        data = fetch_erp("subjects")
        synced = 0
        skipped = 0
        for item in data:
            course = Course.objects.get(course_id=item["course_id"])
            
            # Try department_code first, fallback to course.department
            dept = (Department.objects.filter(code=item.get("department_code")).first() 
                   or course.department)
            
            if not dept:
                print(f"Skipping {item['subject_code']} - no department")
                skipped += 1
                continue
                
            Subject.objects.update_or_create(
                subject_id=item["subject_id"],
                defaults={
                    "subject_code": item["subject_code"],
                    "subject_name": item["subject_name"],
                    "course": course,
                    "department": dept,
                    "semester": item["semester"],
                    "credits": item.get("credits", 4.0),
                    "max_internal": item.get("max_internal", 25),
                    "max_external": item.get("max_external", 75),
                    "total_marks": item.get("total_marks", 100),
                    "is_active": bool(item.get("is_active", 1)),
                },
            )
            synced += 1
        print(f"{schema_name}: {synced} subjects ({skipped} skipped)")
        return {"synced": synced, "skipped": skipped}




@shared_task
def sync_exams(schema_name: str):
    with schema_context(schema_name):
        data = fetch_erp("exams")
        if not data:
            print(f"{schema_name}: no exams data")
            return {"synced": 0}
        
        synced = 0
        skipped = 0
        for item in data:
            try:
                subject = Subject.objects.get(subject_id=item["subject_id"])
                Exam.objects.update_or_create(
                    exam_code=item["exam_code"],
                    defaults={
                        "exam_name": item["exam_name"],
                        "exam_type": item["exam_type"],
                        "max_marks": item["max_marks"],
                        "subject": subject,
                        "semester": item["semester"],
                        "exam_date": parse_iso_date(item["exam_date"]),
                    },
                )
                synced += 1
            except Subject.DoesNotExist:
                print(f"Skipping exam {item['exam_code']} - subject {item['subject_id']} missing")
                skipped += 1
            except Exception as e:
                print(f"Error syncing exam {item['exam_code']}: {e}")
                skipped += 1
        
        print(f"{schema_name}: {synced} exams ({skipped} skipped)")
        return {"synced": synced, "skipped": skipped}



@shared_task
def sync_student_enrollments(schema_name: str):
    with schema_context(schema_name):
        data = fetch_erp("enrollments")
        synced = 0
        skipped = 0
        for item in data:
            try:
                student = StudentProfile.objects.get(roll_number=item["roll_number"])
                subject = Subject.objects.get(subject_code=item["subject_code"])
                StudentSubjectEnrollment.objects.update_or_create(
                    student=student, subject=subject, enrollment_semester=item["enrollment_semester"],
                    defaults={
                        "batch_year": item["batch_year"],
                        "enrollment_date": parse_iso_date(item.get("enrollment_date")),
                        "is_active": bool(item.get("is_active", 1)),
                    },
                )
                synced += 1
            except StudentProfile.DoesNotExist:
                print(f"Skipping enrollment - Student {item['roll_number']} missing")
                skipped += 1
            except Subject.DoesNotExist:
                print(f"Skipping enrollment - Subject {item['subject_code']} missing")
                skipped += 1
            except Exception as e:
                print(f"Enrollment error: {e}")
                skipped += 1
        
        print(f"{schema_name}: {synced} enrollments ({skipped} skipped)")
        return {"synced": synced, "skipped": skipped}



@shared_task
def sync_marks_grades(schema_name: str):
    with schema_context(schema_name):
        data = fetch_erp("marks")
        synced = 0
        skipped = 0
        
        for item in data:
            try:
                student = StudentProfile.objects.get(roll_number=item["roll_number"])
                exam = Exam.objects.get(exam_code=item["exam_code"])
                
                MarksGrades.objects.update_or_create(
                    student=student, exam=exam,
                    defaults={
                        "marks_obtained": item["marks_obtained"],
                        "grade": item.get("grade", ""),
                        "percentage": item.get("percentage"),
                        "is_passed": bool(item.get("is_passed", 0)),
                        "entered_date": parse_iso_date(item.get("entered_date")),  # ✅ Fixed
                    },
                )
                synced += 1
            except Exception as e:
                print(f"Skipping marks {item.get('roll_number')}-{item.get('exam_code')}: {e}")
                skipped += 1
        
        print(f"{schema_name}: {synced} marks ({skipped} skipped)")
        return {"synced": synced, "skipped": skipped}


@shared_task
def sync_placement_records(schema_name: str):
    with schema_context(schema_name):
        data = fetch_erp("placements")
        synced = 0
        skipped = 0
        
        for item in data:
            try:
                student = StudentProfile.objects.get(roll_number=item["roll_number"])
                
                PlacementRecords.objects.update_or_create(
                    student=student, company_name=item["company_name"],
                    defaults={
                        "job_role": item["job_role"],
                        "ctc_offered": item["ctc_offered"],
                        "offer_letter_date": parse_iso_date(item.get("offer_letter_date")),  # ✅ Fixed
                        "joining_date": parse_iso_date(item.get("joining_date")),            # ✅ Fixed
                        "status": item["status"],
                    },
                )
                synced += 1
            except Exception as e:
                print(f"Skipping placement {item.get('roll_number')}: {e}")
                skipped += 1
        
        print(f"{schema_name}: {synced} placements ({skipped} skipped)")
        return {"synced": synced, "skipped": skipped}



@shared_task
def sync_placement_stats(schema_name: str):
    with schema_context(schema_name):
        data = fetch_erp("placement-stats")
        synced = 0
        for item in data:
            dept = Department.objects.get(code=item["department_code"])
            PlacementStats.objects.update_or_create(
                batch_year=item["batch_year"],
                department=dept,
                defaults={
                    "total_students": item["total_students"],
                    "placed_students": item["placed_students"],
                    "placement_percentage": item["placement_percentage"],
                    "avg_ctc": item.get("avg_ctc"),
                    "highest_ctc": item.get("highest_ctc"),
                },
            )
            synced += 1
        print(f"{schema_name}: {synced} placement stats")
        return {"synced": synced}


@shared_task
def sync_alumni(schema_name: str):
    with schema_context(schema_name):
        data = fetch_erp("alumni")
        synced = 0
        skipped = 0
        
        for item in data:
            try:
                student = StudentProfile.objects.get(roll_number=item["roll_number"])
                
                AlumniMaster.objects.update_or_create(
                    student=student,
                    defaults={
                        "graduation_year": item["graduation_year"],
                        "current_organization": item.get("current_organization", ""),
                        "current_designation": item.get("current_designation", ""),
                        "current_ctc": item.get("current_ctc"),
                        "contact_email": item.get("contact_email", ""),
                        "is_active_alumni": bool(item.get("is_active_alumni", 1)),
                    },
                )
                synced += 1
            except StudentProfile.DoesNotExist:
                print(f"Skipping alumni - Student {item['roll_number']} missing")
                skipped += 1
            except Exception as e:
                print(f"Alumni error for {item.get('roll_number')}: {e}")
                skipped += 1
        
        print(f"{schema_name}: {synced} alumni ({skipped} skipped)")
        return {"synced": synced, "skipped": skipped}


@shared_task
def run_full_sync(schema_name: str):
    """
    Orchestrates the full ERP sync in dependency order using Celery chain.
    """
    print(f"Starting full ERP sync for schema: {schema_name}")
    
    # Use chain with .si() (immutable signature) to ignore previous task outputs
    # and pass 'schema_name' explicitly to each.
    workflow = chain(
        sync_users.si(schema_name),
        sync_departments.si(schema_name),
        sync_faculty.si(schema_name),
        sync_students.si(schema_name),
        sync_courses.si(schema_name),
        sync_subjects.si(schema_name),
        sync_exams.si(schema_name),
        sync_student_enrollments.si(schema_name),
        sync_marks_grades.si(schema_name),
        sync_placement_records.si(schema_name),
        sync_placement_stats.si(schema_name),
        sync_alumni.si(schema_name)
    )
    
    workflow.apply_async()
    return f"Triggered full ERP sync for {schema_name}"
