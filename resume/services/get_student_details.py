from django.db.models import Prefetch


def generate_student_details(student):
    """
    Builds a student details dict with optimized DB access.

    Expects `student` to already have select_related/prefetch_related applied,
    OR call prefetch_student_for_resume() first to get the optimized queryset.
    """
    student_profile = student.student_profile
    user = student_profile.user

    # Reuse the prefetched achievements for both the list and skill aggregation
    achievements = list(student_profile.achievements.all())

    student_data = {
        "name": f"{user.first_name} {user.last_name}",
        "email": user.email,
        "phone": student.phone_number,
        "address": student.address,
        "city": student.city,
        "state": student.state,
        "zip_code": student.zip_code,
        "country": student.country,
        "education": [
            {
                "institution": edu.institution_name,
                "board": edu.board_or_university,
                "level": edu.level,
                "score": edu.score,
                "year": edu.passing_year,
            }
            for edu in student_profile.education_history.all()
        ],
        "achievements": [
            {
                "title": ach.title,
                "organization": ach.issuing_organization,
                "date": ach.date_of_event.strftime("%Y-%m-%d")
                if ach.date_of_event
                else None,
                "description": ach.ai_summary or ach.title,
            }
            for ach in achievements
        ],
        "skills": get_aggregated_skills(student_profile, achievements),
    }

    return student_data


def get_aggregated_skills(profile, achievements=None):
    """
    Combines explicit skills from StudentProfile and derived skills from Certificates.
    Uses prefetched data when available to avoid extra queries.
    """
    skills = set()

    # 1. Explicit Skills (uses prefetched M2M if available)
    if hasattr(profile, "skills"):
        skills.update(s.name for s in profile.skills.all())

    # 2. Derived from Certificates (Primary & Secondary)
    if achievements is None:
        achievements = profile.achievements.all()

    for cert in achievements:
        # Primary Skill (select_related makes this free)
        if cert.primary_skill:
            skills.add(cert.primary_skill.name)
        # Secondary Skills (prefetched M2M)
        for skill in cert.secondary_skills.all():
            skills.add(skill.name)

    # Filter None and sort
    return sorted(s for s in skills if s)


def prefetch_user_for_resume(queryset):
    """
    Apply this to a User queryset before calling generate_student_details().
    Collapses ~8 queries into ~3 batched queries.

    Usage:
        user = prefetch_user_for_resume(User.objects.filter(id=request.user.id)).first()
        data = generate_student_details(user)
    """
    return queryset.select_related(
        "student_profile",
    ).prefetch_related(
        "student_profile__education_history",
        "student_profile__skills",
        Prefetch(
            "student_profile__achievements",
            queryset=achievements_queryset(),
        ),
    )


def achievements_queryset():
    """Returns an optimized Certificate queryset with related skills prefetched."""
    from achievements.models import Certificate

    return Certificate.objects.select_related(
        "primary_skill",
    ).prefetch_related(
        "secondary_skills",
    )
