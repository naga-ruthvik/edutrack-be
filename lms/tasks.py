import requests
import uuid
from django_tenants.utils import schema_context
from lms.models import (
    Session, Course, LmsClass, LmsPerson, Enrollment,
    PersonIdentifier, Assignment, Submission
)
from datetime import datetime
from django.utils import timezone  # ← ADD THIS


BASE_URL = "https://ed.link/api/v2"

def get_headers():
    """Replace with your token"""
    return {
        'Authorization': 'Bearer oLlPr9XtJVRmLJNpawvrOGivldn2EzUl',
        'Content-Type': 'application/json'
    }

def fix_date_format(date_str):
    """Convert '2021-08-02T05:00:00.000Z' → '2021-08-02' OR null → TODAY"""
    if not date_str:  # ← NULL/None/empty → TODAY!
        from django.utils import timezone
        return timezone.now().date()  # 2025-12-06
    
    # Extract YYYY-MM-DD from ISO
    return date_str.split('T')[0]  # "2021-08-02T05:00:00.000Z" → "2021-08-02"

def sync_sessions(schema_name):
    """Sync academic sessions for tenant"""
    with schema_context(schema_name):
        headers = get_headers()
        response = requests.get(f'{BASE_URL}/graph/sessions', headers=headers)
        data = response.json()
        
        for session_data in data.get('$data', []):
            Session.objects.update_or_create(
                id=uuid.UUID(session_data['id']),
                defaults={
                    'name': session_data['name'],
                    'start_date': fix_date_format(session_data.get('start_date')),  # null → TODAY!
                    'end_date': fix_date_format(session_data.get('end_date')),      # null → TODAY!
                    'state': session_data.get('state', 'active'),
                    'type': session_data.get('type', 'semester'),
                }
            )
        print(f"✅ {schema_name}: {Session.objects.count()} sessions")

def sync_courses(schema_name):
    """Sync courses for tenant"""  
    with schema_context(schema_name):
        headers = get_headers()
        response = requests.get(f'{BASE_URL}/graph/courses', headers=headers)
        data = response.json()
        
        for course_data in data.get('$data', []):
            Course.objects.update_or_create(
                id=uuid.UUID(course_data['id']),
                defaults={
                    'name': course_data['name'],
                    'code': course_data.get('code', ''),
                    'department': None,  # Admin maps later
                    'session': None,     # Derived from LmsClass.session_ids
                    'created_date': course_data.get('created_date'),
                    'updated_date': course_data.get('updated_date'),
                }
            )
        print(f"✅ {schema_name}: {Course.objects.count()} courses")

def sync_people(schema_name):
    """Sync people/students/teachers [file:501]"""
    with schema_context(schema_name):
        headers = get_headers()
        response = requests.get(f'{BASE_URL}/graph/people', headers=headers)
        data = response.json()
        
        for person_data in data.get('$data', []):
            person, created = LmsPerson.objects.update_or_create(
                id=uuid.UUID(person_data['id']),
                defaults={
                    'first_name': person_data.get('first_name', ''),
                    'last_name': person_data.get('last_name', ''),
                    'display_name': person_data['display_name'],
                    'email': person_data.get('email') or f"{person_data['display_name']}@noemail.com",  # ← FIX!,
                    'roles': person_data.get('roles', []),
                    'django_user': None,
                    'created_date': person_data.get('created_date'),
                    'updated_date': person_data.get('updated_date'),
                }
            )
            
            # Identifiers (canvas_id, sis_id)
            for ident in person_data.get('identifiers', []):
                PersonIdentifier.objects.update_or_create(
                    person=person,
                    type=ident['type'],
                    defaults={'value': ident['value']}
                )
        print(f"✅ {schema_name}: {LmsPerson.objects.count()} people")


def sync_classes(schema_name):
    with schema_context(schema_name):
        headers = get_headers()
        response = requests.get(f'{BASE_URL}/graph/classes', headers=headers)
        data = response.json()
        
        synced = 0
        for class_data in data.get('$data', []):
            try:
                course = Course.objects.get(id=uuid.UUID(class_data['course_id']))
                LmsClass.objects.update_or_create(
                    id=uuid.UUID(class_data['id']),
                    defaults={
                        'name': class_data['name'],
                        'state': class_data.get('state', 'active'),
                        'course': course,
                        'session_ids': class_data.get('session_ids', []),
                        'enrollment_count': class_data.get('references', {}).get('enrollments', 0),
                        'created_date': class_data.get('created_date'),
                        'updated_date': class_data.get('updated_date'),
                    }
                )
                synced += 1
            except Course.DoesNotExist:
                continue
        print(f"✅ {schema_name}: {LmsClass.objects.count()} classes")

def sync_enrollments(schema_name):
    """Sync enrollments - BULLETPROOF"""
    with schema_context(schema_name):
        headers = get_headers()
        response = requests.get(f'{BASE_URL}/graph/enrollments', headers=headers)
        data = response.json()
        
        synced = 0
        skipped = 0
        
        for enroll_data in data.get('$data', []):
            try:
                person = LmsPerson.objects.get(id=uuid.UUID(enroll_data['person_id']))
                class_section = LmsClass.objects.get(id=uuid.UUID(enroll_data['class_id']))
                
                Enrollment.objects.update_or_create(
                    id=uuid.UUID(enroll_data['id']),
                    defaults={
                        'person': person,
                        'class_section': class_section,
                        'role': enroll_data['role'],
                        'state': enroll_data.get('state', 'active'),
                        'final_letter_grade': enroll_data.get('final_letter_grade'),
                        'final_numeric_grade': enroll_data.get('final_numeric_grade'),
                        'start_date': enroll_data.get('start_date'),
                        'end_date': enroll_data.get('end_date'),
                        'created_date': enroll_data.get('created_date'),
                        'updated_date': enroll_data.get('updated_date'),
                    }
                )
                synced += 1
            except (LmsPerson.DoesNotExist, LmsClass.DoesNotExist):
                skipped += 1
                continue
            except Exception:
                skipped += 1
                continue
        
        students = Enrollment.objects.filter(role='student').count()
        teachers = Enrollment.objects.filter(role='teacher').count()
        print(f"✅ {schema_name}: {students} students, {teachers} teachers")

def sync_assignments(schema_name):
    """Sync assignments/quizzes"""
    with schema_context(schema_name):
        headers = get_headers()
        response = requests.get(f'{BASE_URL}/graph/assignments', headers=headers)
        data = response.json()
        
        for assign_data in data.get('$data', []):
            class_section = LmsClass.objects.get(id=uuid.UUID(assign_data['class_id']))
            
            Assignment.objects.update_or_create(
                id=uuid.UUID(assign_data['id']),
                defaults={
                    'class_section': class_section,
                    'title': assign_data['title'],
                    'state': assign_data.get('state', 'open'),
                    'due_date': assign_data['due_date'],
                    'points_possible': assign_data.get('points_possible', 0),
                    'grading_type': assign_data.get('grading_type', 'points'),
                }
            )
        print(f"✅ {schema_name}: {Assignment.objects.count()} assignments")

def sync_submissions(schema_name):
    """Sync student submissions"""
    with schema_context(schema_name):
        headers = get_headers()
        response = requests.get(f'{BASE_URL}/graph/submissions', headers=headers)
        data = response.json()
        
        for submission_data in data.get('$data', []):
            assignment = Assignment.objects.get(id=uuid.UUID(submission_data['assignment_id']))
            student = LmsPerson.objects.get(id=uuid.UUID(submission_data['student_id']))
            
            Submission.objects.update_or_create(
                id=uuid.UUID(submission_data['id']),
                defaults={
                    'assignment': assignment,
                    'student': student,
                    'submitted_at': submission_data.get('submitted_at'),
                    'grade_points': submission_data.get('grade_points'),
                    'override_due_date': submission_data.get('override_due_date'),
                    'created_date': submission_data.get('created_date'),
                    'updated_date': submission_data.get('updated_date'),
                }
            )
        print(f"✅ {schema_name}: {Submission.objects.count()} submissions")
