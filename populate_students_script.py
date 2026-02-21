import os
import django
import sys

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edutrack.settings')
sys.path.insert(0, 'c:\\Users\\konde\\main-projects\\EduTrack\\edutrack')

django.setup()

from django_tenants.utils import schema_context
from authentication.models import User
from profiles.models import StudentProfile, Education
from academics.models import Department
from faker import Faker
import random

faker = Faker()

# Use vardhaman tenant
with schema_context('vardhaman'):
    print(f"Current schema: vardhaman")
    
    # Check departments
    departments = list(Department.objects.all())
    print(f"Found {len(departments)} departments: {[d.code for d in departments]}")
    
    if not departments:
        print("ERROR: No departments found!")
        sys.exit(1)
    
    # Create 20 fake students
    for i in range(20):
        try:
            first_name = faker.first_name()
            last_name = faker.last_name()
            username = f"{first_name.lower()}.{last_name.lower()}{random.randint(100, 999)}"
            email = f"{username}@vardhaman.edu"
            
            # Create User
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=User.Role.STUDENT,
                password='Student@123'
            )
            
            # Generate roll number
            dept = random.choice(departments)
            roll_number = f"{dept.code}{random.randint(1000, 9999)}"
            
            # Create Student Profile
            student_profile = StudentProfile.objects.create(
                user=user,
                roll_number=roll_number,
                department=dept,
                batch_year=random.choice([2021, 2022, 2023, 2024]),
                current_semester=random.randint(1, 8)
            )
            
            # Add Class 10 education
            Education.objects.create(
                student=student_profile,
                institution_name=faker.company() + " High School",
                board_or_university="CBSE",
                level=Education.Level.SCHOOL_10,
                score=f"{random.randint(80, 95)}%",
                passing_year=random.randint(2015, 2019)
            )
            
            # Add Class 12 education
            Education.objects.create(
                student=student_profile,
                institution_name=faker.company() + " Senior Secondary School",
                board_or_university="State Board",
                level=Education.Level.SCHOOL_12,
                score=f"{random.randint(75, 95)}%",
                passing_year=random.randint(2017, 2021)
            )
            
            print(f"✓ Created student {i+1}/20: {user.get_full_name()} ({roll_number})")
            
        except Exception as e:
            print(f"✗ Error creating student {i+1}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\nCompleted! Default password for all students: Student@123")
