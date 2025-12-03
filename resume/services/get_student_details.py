import json

def generate_student_details(student):
    student_profile=student.student_profile
    student_data={
        "name":student_profile.user.first_name+" "+student_profile.user.last_name,
        "email":student_profile.user.email,
        "phone":student.phone_number,
        "address":student.address,
        "city":student.city,
        "state":student.state,
        "zip_code":student.zip_code,
        "country":student.country,
        "education": [
            {
                "institution": edu.institution_name,
                "board": edu.board_or_university,
                "level": edu.level,
                "score": edu.score,
                "year": edu.passing_year
            } for edu in student_profile.education_history.all()
        ],
        # "skills":student_profile.skills,
        # "experience":student_profile.experience,
        # "projects":student_profile.projects,
        "achievements": [
            {
                "title": ach.title,
                "organization": ach.issuing_organization,
                "date": ach.date_of_event.strftime('%Y-%m-%d') if ach.date_of_event else None,
                "description": ach.ai_summary or ach.title
            } for ach in student_profile.achievements.all()
        ]
    }

    return student_data

