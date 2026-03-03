# profiles/views/__init__.py
# Re-export all views so imports like `from profiles.views import StudentListView` work.

from profiles.views.student import (
    StudentListCreateView,
    StudentDetailView,
    student_total_view,
    student_data_view,
)

from profiles.views.faculty import (
    HODCreateView,
    HODListView,
    FacultyMenteeListView,
)

from profiles.views.bulk import (
    BulkProfileUploadView,
)
