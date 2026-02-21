from django.core.management.base import BaseCommand
from django.db import connection
from authentication.models import User
from profiles.models import StudentProfile, Education
from academics.models import Department
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Populate the current tenant with fake student data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of fake students to create (default: 20)'
        )

    def handle(self, *args, **options):
        count = options['count']
        fake = Faker()
        
        # Get the current tenant schema
        tenant_schema = connection.schema_name
        self.stdout.write(f"Populating tenant: {tenant_schema}")
        
        # Check if departments exist
        departments = list(Department.objects.all())
        if not departments:
            self.stdout.write(self.style.ERROR('No departments found. Please create departments first.'))
            return
        
        self.stdout.write(f"Found {len(departments)} departments")
        
        created_students = []
        
        for i in range(count):
            try:
                # Generate unique username and email
                first_name = fake.first_name()
                last_name = fake.last_name()
                username = f"{first_name.lower()}.{last_name.lower()}{random.randint(100, 999)}"
                email = f"{username}@{tenant_schema}.edu"
                
                # Create User
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role=User.Role.STUDENT,
                    password='Student@123'  # Default password for all fake students
                )
                
                # Generate unique roll number
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
                
                # Add education history
                # Class 10
                Education.objects.create(
                    student=student_profile,
                    institution_name=fake.company() + " High School",
                    board_or_university="CBSE",
                    level=Education.Level.SCHOOL_10,
                    score=f"{random.randint(80, 95)}%",
                    passing_year=random.randint(2015, 2019)
                )
                
                # Class 12
                Education.objects.create(
                    student=student_profile,
                    institution_name=fake.company() + " Senior Secondary School",
                    board_or_university="State Board",
                    level=Education.Level.SCHOOL_12,
                    score=f"{random.randint(75, 95)}%",
                    passing_year=random.randint(2017, 2021)
                )
                
                created_students.append(student_profile)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created student {i+1}/{count}: {user.get_full_name()} ({roll_number})"
                    )
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error creating student {i+1}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully created {len(created_students)} students in tenant '{tenant_schema}'"
            )
        )
        self.stdout.write(f"Default password for all students: Student@123")
