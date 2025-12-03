import os
import django
import json
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edutrack.settings')
django.setup()

from django.db import connection
from profiles.models import StudentProfile, Education
from achievements.models import Certificate
from resume.services.get_student_details import generate_student_details

# Set schema
connection.set_schema('vmeg')

try:
    # Get a student profile (assuming one exists, or we'll handle the error)
    student_profile = StudentProfile.objects.first()
    
    if not student_profile:
        print("No student profile found to test with.")
    else:
        print(f"Testing with student: {student_profile}")
        
        # Ensure there's some dummy data for education and achievements if missing
        # Check if education exists, if not try to create, but wrap in try-except
        if not student_profile.education_history.exists():
            print("Creating dummy education data...")
            try:
                Education.objects.create(
                    student=student_profile,
                    institution_name="Test School",
                    board_or_university="CBSE",
                    level="12",
                    score="90%",
                    passing_year=2020
                )
            except Exception as e:
                print(f"Could not create education data: {e}")
            
        if not student_profile.achievements.exists():
            print("Creating dummy achievement data...")
            try:
                Certificate.objects.create(
                    student=student_profile,
                    title="Test Certificate",
                    issuing_organization="Test Org",
                    date_of_event="2023-01-01"
                )
            except Exception as e:
                print(f"Could not create achievement data: {e}")

        # Call the function with the User object
        print("Calling generate_student_details...")
        try:
            data = generate_student_details(student_profile.user)
            print(json.dumps(data, indent=4, default=str))
        except AttributeError as e:
            print(f"AttributeError during generation: {e}")
            # Debug what 'student' has
            u = student_profile.user
            print(f"User attributes: {dir(u)}")

except Exception as e:
    print(f"Error: {e}")
