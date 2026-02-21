from django.contrib import admin
from profiles.models import StudentProfile, FacultyProfile, Education


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = [
        "roll_number",
        "user",
        "department",
        "batch_year",
        "current_semester",
    ]
    list_filter = ["department", "batch_year", "current_semester"]
    search_fields = [
        "roll_number",
        "user__first_name",
        "user__last_name",
        "user__email",
    ]
    raw_id_fields = ["user", "mentor"]


@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ["employee_id", "user", "department", "designation", "is_hod"]
    list_filter = ["department", "designation", "is_hod"]
    search_fields = ["employee_id", "user__first_name", "user__last_name"]
    raw_id_fields = ["user"]


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ["student", "level", "institution_name", "score", "passing_year"]
    list_filter = ["level", "passing_year"]
    search_fields = ["institution_name", "student__roll_number"]
