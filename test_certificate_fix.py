import os
import django
from django.conf import settings
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edutrack.settings')
django.setup()

from achievements.models import Certificate, Skill
from profiles.models import StudentProfile
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

User = get_user_model()

def test_certificate_creation():
    schema_name = 'anvesh' 
    print(f"Testing in schema: {schema_name}")
    
    with schema_context(schema_name):
        # 1. Get or Create a Student
        # We need a user and a student profile
        try:
            user = User.objects.first()
            if not user:
                print("No users found. Creating one.")
                user = User.objects.create_user(username='testuser', password='password')
            
            student, created = StudentProfile.objects.get_or_create(user=user, defaults={'roll_number': '12345'})
            print(f"Using student: {student}")

            # 2. Ensure Skills exist
            python_skill, _ = Skill.objects.get_or_create(name='python')
            
            # 3. Create Certificate WITHOUT primary_skill (The Fix)
            print("Attempting to create certificate without primary_skill...")
            cert = Certificate.objects.create(
                student=student,
                title="Test Certificate",
                issuing_organization="Test Org",
                file_url="http://example.com/cert.pdf",
                category="OTHER",
                academic_year="2024-25",
                ai_summary="Summary",
                level="COLLEGE",
                rank="PARTICIPATION",
                status="PENDING",
                credit_points=0
            )
            
            # 4. Add Secondary Skills (The Logic Update)
            cert.secondary_skills.add(python_skill)
            
            print(f"Certificate created successfully: {cert}")
            print(f"Primary Skill: {cert.primary_skill}")
            print(f"Secondary Skills: {list(cert.secondary_skills.all())}")
            
            assert cert.primary_skill is None
            assert python_skill in cert.secondary_skills.all()
            print("VERIFICATION SUCCESSFUL: IntegrityError avoided and skills added.")

        except Exception as e:
            print(f"VERIFICATION FAILED: {e}")
            # import traceback
            # traceback.print_exc()
            
            print("--- COLUMN POSITIONS ---")
            with connection.cursor() as cursor:
                cursor.execute("SELECT column_name, ordinal_position FROM information_schema.columns WHERE table_name = 'achievements_certificate' ORDER BY ordinal_position;")
                columns = cursor.fetchall()
            print("--- RAW SQL INSERT ---")
            with connection.cursor() as cursor:
                try:
                    cursor.execute("""
                        INSERT INTO achievements_certificate 
                        (title, issuing_organization, file_url, student_id, created_at, updated_at, status, credit_points, level, rank, category, academic_year, ai_summary, ocr_text, primary_skill_id)
                        VALUES 
                        ('Raw SQL Cert', 'Org', 'url', %s, NOW(), NOW(), 'PENDING', 0, 'COLLEGE', 'PARTICIPATION', '', '', '', '', NULL)
                    """, [student.id])
                    print("RAW SQL INSERT SUCCESSFUL")
                except Exception as e:
                    print(f"RAW SQL INSERT FAILED: {e}")
            
            return

            # Retry creation
            print("Retrying creation...")
            cert = Certificate.objects.create(
                student=student,
                title="Test Certificate",
                issuing_organization="Test Org",
                file_url="http://example.com/cert.pdf",
                category="OTHER",
                academic_year="2024-25",
                ai_summary="Summary",
                level="COLLEGE",
                rank="PARTICIPATION",
                status="PENDING",
                credit_points=0
            )
            
            # 4. Add Secondary Skills (The Logic Update)
            cert.secondary_skills.add(python_skill)
            
            print(f"Certificate created successfully: {cert}")
            print(f"Primary Skill: {cert.primary_skill}")
            print(f"Secondary Skills: {list(cert.secondary_skills.all())}")
            
            assert cert.primary_skill is None
            assert python_skill in cert.secondary_skills.all()
            print("VERIFICATION SUCCESSFUL: IntegrityError avoided and skills added.")

if __name__ == "__main__":
    test_certificate_creation()
