# erp/tasks.py - Academic ERP Data Only (excluding users/faculty/students/departments)
import requests
import logging
from django.db import transaction
from profiles.models import StudentProfile
from academics.models import Department
from .models import (
    Course, Subject, StudentSubjectEnrollment, Exam, MarksGrades,
    PlacementRecords, PlacementStats, AlumniMaster
)

logger = logging.getLogger(__name__)
ERP_BASE_URL = "https://backend-erp-zeta.vercel.app/api"

@shared_task
def sync_academic_erp_data():
    with transaction.atomic():
        results = {
            'courses': sync_courses(),
            'subjects': sync_subjects(),
            'exams': sync_exams(),
            'enrollments': sync_student_enrollments(),
            'marks': sync_marks_grades(),
            'placements': sync_placement_records(),
            'stats': sync_placement_stats(),
            'alumni': sync_alumni()
        }
        return results

def fetch_erp_data(endpoint):
    try:
        url = f"{ERP_BASE_URL}/{endpoint}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get('data', []) if data.get('success') else []
    except requests.RequestException:
        return []

def sync_courses():
    courses_data = fetch_erp_data('courses')
    count = 0
    for course_data in courses_data:
        try:
            dept = Department.objects.get(id=course_data['department_id'])
            Course.objects.update_or_create(
                course_id=course_data['course_id'],
                defaults={
                    'course_code': course_data['course_code'],
                    'course_name': course_data['course_name'],
                    'department': dept,
                    'duration_years': course_data.get('duration_years', 4),
                    'total_credits': course_data.get('total_credits', 160),
                    'intake_capacity': course_data.get('intake_capacity', 60),
                    'is_active': course_data.get('is_active', True),
                }
            )
            count += 1
        except Department.DoesNotExist:
            continue
    return {'synced': count}

def sync_subjects():
    subjects_data = fetch_erp_data('subjects')
    count = 0
    for subject_data in subjects_data:
        try:
            dept = Department.objects.get(id=subject_data['department_id'])
            course = Course.objects.get(course_id=subject_data['course_id'])
            Subject.objects.update_or_create(
                subject_id=subject_data['subject_id'],
                defaults={
                    'subject_code': subject_data['subject_code'],
                    'subject_name': subject_data['subject_name'],
                    'course': course,
                    'department': dept,
                    'semester': subject_data['semester'],
                    'credits': subject_data['credits'],
                    'max_internal': subject_data.get('max_internal', 25),
                    'max_external': subject_data.get('max_external', 75),
                    'total_marks': subject_data.get('total_marks', 100),
                    'is_active': subject_data.get('is_active', True),
                }
            )
            count += 1
        except (Department.DoesNotExist, Course.DoesNotExist):
            continue
    return {'synced': count}

def sync_exams():
    exams_data = fetch_erp_data('exams')
    count = 0
    for exam_data in exams_data:
        try:
            subject = Subject.objects.get(subject_id=exam_data['subject_id'])
            Exam.objects.update_or_create(
                exam_code=exam_data['exam_code'],
                defaults={
                    'exam_name': exam_data['exam_name'],
                    'exam_type': exam_data['exam_type'],
                    'max_marks': exam_data['max_marks'],
                    'subject': subject,
                    'semester': exam_data['semester'],
                    'exam_date': exam_data['exam_date'],
                }
            )
            count += 1
        except Subject.DoesNotExist:
            continue
    return {'synced': count}

def sync_student_enrollments():
    enrollments_data = fetch_erp_data('enrollments')
    count = 0
    for enrollment_data in enrollments_data:
        try:
            student = StudentProfile.objects.get(profile_id=enrollment_data['student_id'])
            subject = Subject.objects.get(subject_id=enrollment_data['subject_id'])
            StudentSubjectEnrollment.objects.update_or_create(
                student=student,
                subject=subject,
                enrollment_semester=enrollment_data['enrollment_semester'],
                defaults={
                    'batch_year': enrollment_data['batch_year'],
                    'enrollment_date': enrollment_data.get('enrollment_date'),
                    'is_active': enrollment_data.get('is_active', True),
                }
            )
            count += 1
        except (StudentProfile.DoesNotExist, Subject.DoesNotExist):
            continue
    return {'synced': count}

def sync_marks_grades():
    marks_data = fetch_erp_data('marks')
    count = 0
    for mark_data in marks_data:
        try:
            student = StudentProfile.objects.get(profile_id=mark_data['student_id'])
            exam = Exam.objects.get(exam_id=mark_data['exam_id'])
            MarksGrades.objects.update_or_create(
                student=student,
                exam=exam,
                defaults={
                    'marks_obtained': mark_data['marks_obtained'],
                    'grade': mark_data.get('grade'),
                    'percentage': mark_data.get('percentage'),
                    'is_passed': mark_data.get('is_passed', False),
                    'entered_date': mark_data.get('entered_date'),
                }
            )
            count += 1
        except (StudentProfile.DoesNotExist, Exam.DoesNotExist):
            continue
    return {'synced': count}

def sync_placement_records():
    placements_data = fetch_erp_data('placements')
    count = 0
    for placement_data in placements_data:
        try:
            student = StudentProfile.objects.get(profile_id=placement_data['student_id'])
            PlacementRecords.objects.update_or_create(
                student=student,
                company_name=placement_data['company_name'],
                defaults={
                    'job_role': placement_data['job_role'],
                    'ctc_offered': placement_data['ctc_offered'],
                    'offer_letter_date': placement_data.get('offer_letter_date'),
                    'joining_date': placement_data.get('joining_date'),
                    'status': placement_data['status'],
                }
            )
            count += 1
        except StudentProfile.DoesNotExist:
            continue
    return {'synced': count}

def sync_placement_stats():
    stats_data = fetch_erp_data('placement-stats')
    count = 0
    for stat_data in stats_data:
        try:
            dept = Department.objects.get(id=stat_data['department_id'])
            PlacementStats.objects.update_or_create(
                batch_year=stat_data['batch_year'],
                department=dept,
                defaults={
                    'total_students': stat_data['total_students'],
                    'placed_students': stat_data['placed_students'],
                    'placement_percentage': stat_data['placement_percentage'],
                    'avg_ctc': stat_data.get('avg_ctc'),
                    'highest_ctc': stat_data.get('highest_ctc'),
                }
            )
            count += 1
        except Department.DoesNotExist:
            continue
    return {'synced': count}

def sync_alumni():
    alumni_data = fetch_erp_data('alumni')
    count = 0
    for alum_data in alumni_data:
        try:
            student = StudentProfile.objects.get(profile_id=alum_data['student_id'])
            AlumniMaster.objects.update_or_create(
                student=student,
                defaults={
                    'graduation_year': alum_data['graduation_year'],
                    'current_organization': alum_data.get('current_organization'),
                    'current_designation': alum_data.get('current_designation'),
                    'current_ctc': alum_data.get('current_ctc'),
                    'contact_email': alum_data.get('contact_email'),
                    'is_active_alumni': alum_data.get('is_active_alumni', True),
                }
            )
            count += 1
        except StudentProfile.DoesNotExist:
            continue
    return {'synced': count}
