import os
import django
import sys
from datetime import date, timedelta
import random

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edutrack.settings")
sys.path.insert(0, "c:\\Users\\konde\\main-projects\\EduTrack\\edutrack")

django.setup()

from django_tenants.utils import schema_context
from profiles.models import StudentProfile
from achievements.models import Certificate, Skill

# Use vardhaman tenant
with schema_context("vardhaman"):
    print("Current schema: vardhaman")

    # Find student with roll number F5
    try:
        student = StudentProfile.objects.get(roll_number="F5")
        print(f"Found student: {student.user.get_full_name()} ({student.roll_number})")
    except StudentProfile.DoesNotExist:
        print("ERROR: Student with roll number 'F5' not found!")
        sys.exit(1)

    # Create or get skills
    skills_data = [
        "python",
        "machine learning",
        "web development",
        "data analysis",
        "react",
        "django",
        "sql",
        "leadership",
        "public speaking",
        "research",
        "javascript",
        "artificial intelligence",
    ]

    skills = []
    for skill_name in skills_data:
        skill, created = Skill.objects.get_or_create(name=skill_name.lower())
        skills.append(skill)
        if created:
            print(f"  Created skill: {skill_name}")

    print(f"\nTotal skills: {len(skills)}")

    # Now create diverse achievements for student F5
    achievements_data = [
        # MOOC Certifications
        {
            "title": "Machine Learning Specialization",
            "issuing_organization": "Coursera - Stanford University",
            "category": Certificate.Category.MOOC,
            "level": Certificate.Level.INTERNATIONAL,
            "rank": Certificate.Rank.PARTICIPATION,
            "primary_skill": "machine learning",
            "secondary_skills": ["python", "data analysis"],
            "date_of_event": date.today() - timedelta(days=180),
            "verification_url": "https://www.coursera.org/account/accomplishments/verify/ABCD1234",
            "ai_summary": "Completed comprehensive ML course covering supervised and unsupervised learning algorithms",
            "status": Certificate.Status.AI_VERIFIED,
            "credit_points": 15,
        },
        {
            "title": "Full Stack Web Development with React",
            "issuing_organization": "Coursera - Hong Kong University",
            "category": Certificate.Category.MOOC,
            "level": Certificate.Level.INTERNATIONAL,
            "rank": Certificate.Rank.PARTICIPATION,
            "primary_skill": "react",
            "secondary_skills": ["web development", "javascript"],
            "date_of_event": date.today() - timedelta(days=120),
            "verification_url": "https://www.coursera.org/account/accomplishments/verify/EFGH5678",
            "ai_summary": "Mastered React, Redux, and modern web development practices",
            "status": Certificate.Status.AI_VERIFIED,
            "credit_points": 12,
        },
        # Internships
        {
            "title": "Software Development Intern",
            "issuing_organization": "Tech Solutions Pvt Ltd",
            "category": Certificate.Category.INTERNSHIP,
            "level": Certificate.Level.NATIONAL,
            "rank": Certificate.Rank.PARTICIPATION,
            "primary_skill": "web development",
            "secondary_skills": ["python", "django", "sql"],
            "date_of_event": date.today() - timedelta(days=90),
            "ai_summary": "Worked on backend development using Django and PostgreSQL for 3 months",
            "status": Certificate.Status.MANUAL_VERIFIED,
            "credit_points": 20,
        },
        # Projects
        {
            "title": "AI-Based Student Performance Prediction System",
            "issuing_organization": "Final Year Project - Vardhaman College",
            "category": Certificate.Category.PROJECT,
            "level": Certificate.Level.COLLEGE,
            "rank": Certificate.Rank.WINNER,
            "primary_skill": "artificial intelligence",
            "secondary_skills": ["machine learning", "python", "data analysis"],
            "date_of_event": date.today() - timedelta(days=60),
            "ai_summary": "Developed ML model to predict student performance with 87% accuracy using Random Forest",
            "status": Certificate.Status.MANUAL_VERIFIED,
            "credit_points": 25,
        },
        # Technical/Hackathon
        {
            "title": "Second Prize - Smart India Hackathon 2024",
            "issuing_organization": "Ministry of Education, Government of India",
            "category": Certificate.Category.TECHNICAL,
            "level": Certificate.Level.NATIONAL,
            "rank": Certificate.Rank.SECOND,
            "primary_skill": "web development",
            "secondary_skills": ["react", "python", "leadership"],
            "date_of_event": date.today() - timedelta(days=150),
            "ai_summary": "Led team of 6 to build EdTech solution for rural education, won 2nd prize nationally",
            "status": Certificate.Status.MANUAL_VERIFIED,
            "credit_points": 30,
        },
        # Research
        {
            "title": "Research Paper: Deep Learning in Agricultural Automation",
            "issuing_organization": "IEEE International Conference on AI",
            "category": Certificate.Category.RESEARCH,
            "level": Certificate.Level.INTERNATIONAL,
            "rank": Certificate.Rank.PARTICIPATION,
            "primary_skill": "research",
            "secondary_skills": ["artificial intelligence", "machine learning"],
            "date_of_event": date.today() - timedelta(days=200),
            "verification_url": "https://ieeexplore.ieee.org/document/12345678",
            "ai_summary": "Published research on CNN-based crop disease detection with 92% accuracy",
            "status": Certificate.Status.MANUAL_VERIFIED,
            "credit_points": 35,
        },
        # Cultural
        {
            "title": "Winner - Technical Paper Presentation",
            "issuing_organization": "TechFest 2024 - IIT Bombay",
            "category": Certificate.Category.CULTURAL,
            "level": Certificate.Level.NATIONAL,
            "rank": Certificate.Rank.FIRST,
            "primary_skill": "public speaking",
            "secondary_skills": ["leadership", "research"],
            "date_of_event": date.today() - timedelta(days=100),
            "ai_summary": "Won 1st prize in technical paper presentation on blockchain in education",
            "status": Certificate.Status.AI_VERIFIED,
            "credit_points": 18,
        },
        # Extension Activities
        {
            "title": "NSS Volunteer - Blood Donation Camp Coordinator",
            "issuing_organization": "National Service Scheme",
            "category": Certificate.Category.EXTENSION,
            "level": Certificate.Level.STATE,
            "rank": Certificate.Rank.PARTICIPATION,
            "primary_skill": "leadership",
            "date_of_event": date.today() - timedelta(days=250),
            "ai_summary": "Coordinated blood donation camp, collected 150+ units, helped 200+ donors",
            "status": Certificate.Status.MANUAL_VERIFIED,
            "credit_points": 10,
        },
    ]

    created_achievements = []

    for i, ach_data in enumerate(achievements_data):
        try:
            # Get primary skill
            primary_skill = Skill.objects.get(name=ach_data["primary_skill"].lower())

            # Create achievement (without file since user doesn't want files)
            achievement = Certificate.objects.create(
                student=student,
                title=ach_data["title"],
                issuing_organization=ach_data["issuing_organization"],
                category=ach_data["category"],
                level=ach_data["level"],
                rank=ach_data["rank"],
                primary_skill=primary_skill,
                date_of_event=ach_data["date_of_event"],
                verification_url=ach_data.get("verification_url", ""),
                ai_summary=ach_data["ai_summary"],
                status=ach_data["status"],
                credit_points=ach_data["credit_points"],
            )

            # Add secondary skills if any
            if "secondary_skills" in ach_data:
                for sec_skill_name in ach_data["secondary_skills"]:
                    sec_skill = Skill.objects.get(name=sec_skill_name.lower())
                    achievement.secondary_skills.add(sec_skill)

            created_achievements.append(achievement)
            print(
                f"✓ Created achievement {i + 1}/8: {achievement.title} ({achievement.get_category_display()})"
            )

        except Exception as e:
            print(f"✗ Error creating achievement {i + 1}: {str(e)}")
            import traceback

            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(
        f"SUCCESS! Created {len(created_achievements)} achievements for {student.user.get_full_name()}"
    )
    print(f"{'=' * 60}")
    print(f"\nAchievement Summary:")
    print(
        f"  - Total Credit Points: {sum(a.credit_points for a in created_achievements)}"
    )
    print(
        f"  - MOOCs: {len([a for a in created_achievements if a.category == Certificate.Category.MOOC])}"
    )
    print(
        f"  - Internships: {len([a for a in created_achievements if a.category == Certificate.Category.INTERNSHIP])}"
    )
    print(
        f"  - Projects: {len([a for a in created_achievements if a.category == Certificate.Category.PROJECT])}"
    )
    print(
        f"  - Technical/Hackathons: {len([a for a in created_achievements if a.category == Certificate.Category.TECHNICAL])}"
    )
    print(
        f"  - Research: {len([a for a in created_achievements if a.category == Certificate.Category.RESEARCH])}"
    )
    print(
        f"  - Cultural: {len([a for a in created_achievements if a.category == Certificate.Category.CULTURAL])}"
    )
    print(
        f"  - Extension/Outreach: {len([a for a in created_achievements if a.category == Certificate.Category.EXTENSION])}"
    )
