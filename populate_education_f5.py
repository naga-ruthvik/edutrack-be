import os
import django
import sys

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edutrack.settings')
sys.path.insert(0, 'c:\\Users\\konde\\main-projects\\EduTrack\\edutrack')

django.setup()

from django_tenants.utils import schema_context
from profiles.models import StudentProfile, Education

# Use vardhaman tenant
with schema_context('vardhaman'):
    print(f"Current schema: vardhaman")
    
    # Find student with roll number F5
    try:
        student = StudentProfile.objects.get(roll_number='F5')
        print(f"Found student: {student.user.get_full_name()} ({student.roll_number})")
    except StudentProfile.DoesNotExist:
        print("ERROR: Student with roll number 'F5' not found!")
        sys.exit(1)
    
    # Check existing education records
    existing_count = student.education_history.count()
    print(f"Existing education records: {existing_count}")
    
    if existing_count > 0:
        print("\nStudent already has education records. Skipping...")
        sys.exit(0)
    
    # Create comprehensive education history
    education_data = [
        {
            'level': Education.Level.SCHOOL_10,
            'institution_name': 'Delhi Public School, Hyderabad',
            'board_or_university': 'CBSE',
            'score': '9.8 CGPA',
            'passing_year': 2018
        },
        {
            'level': Education.Level.SCHOOL_12,
            'institution_name': 'Narayana Junior College, Hyderabad',
            'board_or_university': 'Board of Intermediate Education, Telangana',
            'score': '97.5%',
            'passing_year': 2020
        },
        {
            'level': Education.Level.UNDERGRAD,
            'institution_name': 'Vardhaman College of Engineering',
            'board_or_university': 'JNTUH (Jawaharlal Nehru Technological University Hyderabad)',
            'score': '8.9 CGPA',
            'passing_year': 2024
        }
    ]
    
    created_records = []
    
    for edu_data in education_data:
        try:
            education = Education.objects.create(
                student=student,
                institution_name=edu_data['institution_name'],
                board_or_university=edu_data['board_or_university'],
                level=edu_data['level'],
                score=edu_data['score'],
                passing_year=edu_data['passing_year']
            )
            
            created_records.append(education)
            print(f"✓ Created: {education.get_level_display()} - {education.institution_name} ({education.score})")
            
        except Exception as e:
            print(f"✗ Error creating education record: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"SUCCESS! Created {len(created_records)} education records for {student.user.get_full_name()}")
    print(f"{'='*60}")
    
    print(f"\nEducation Summary:")
    for edu in student.education_history.all().order_by('passing_year'):
        print(f"  {edu.passing_year} - {edu.get_level_display()}: {edu.institution_name}")
        print(f"           {edu.board_or_university} - {edu.score}")
