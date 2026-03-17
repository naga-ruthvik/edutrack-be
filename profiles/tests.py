from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from django.urls import reverse

from academics.models import Department
from authentication.models import User

from .models import FacultyProfile, StudentProfile


class TenantAPIClient(TenantClient, APIClient):
    def __init__(self, tenant, **defaults):
        super().__init__(tenant, **defaults)


class BaseTenantTestCase(TenantTestCase):
    def setUpStudent(self):
        super().setUp()
        self.client = TenantAPIClient(self.tenant)
        self.user = User.objects.create_user(
            username="student", password="", role=User.Role.STUDENT
        )
        self.department = Department.objects.create(name="", code="")
        self.student = StudentProfile.objects.create(
            user=self.user, department=self.department
        )

    def setUpFaculty(self):
        super().setUp()
        self.client = TenantAPIClient(self.tenant)
        self.user = User.objects.create_user(
            username="faculty", password="", role=User.Role.FACULTY
        )
        self.department = Department.objects.create(name="", code="")
        self.faculty = FacultyProfile.objects.create(
            user=self.user, department=self.department
        )

    def setUpHOD(self):
        self.setUpFaculty()
        self.faculty.is_hod = True
        self.faculty.save()

    def setUpAdmin(self):
        super().setUp()
        self.client = TenantAPIClient(self.tenant)
        self.user = User.objects.create_user(
            username="admin", password="", role=User.Role.ADMIN
        )

    def authenticate_user(self, user=None):
        self.client.force_authenticate(user=user or self.user)


# Create your tests here.
class StudentProfileTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUpStudent()

    def test_is_student(self):
        self.authenticate_user(self.user)
        role = self.user.role
        self.assertEqual(role, User.Role.STUDENT)
        self.assertEqual(self.student.user, self.user)

    def test_list_student_success(self):
        self.authenticate_user()
        url = reverse("student_list_create")
        response = self.client.get(url)
        # happy check
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # structure
        self.assertGreaterEqual(len(response.data), 1)
        self.assertIsInstance(response.data, list)

        # fields
        student = response.data[0]
        self.assertIn("id", student)
        self.assertIn("roll_number", student)
        self.assertIn("department", student)
        self.assertIn("user", student)

        # data correctness
        self.assertEqual(self.user.id, student["user"]["id"])

    def test_student_detail(self):
        self.authenticate_user(self.user)
        user_id = self.user.id
        url = reverse("student_detail", args=(user_id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_student_create(self):
        self.authenticate_user(self.user)
        url = reverse("student_list_create")
        student_data = {
            "user": {
                "password": "fsafsdfds",
                "email": "test@mail.co",
            },
            "roll_number": "233253534",
            "department": self.department.id,
        }
        response = self.client.post(url, student_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_student_data(self):
        self.authenticate_user(self.user)
        user_id = self.user.id
        url = reverse("student_data")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # TODO: move this API test to admin test class
    # def test_student_count(self):
    #     self.authenticate_user(self.user)
    #     url = reverse("student_total")
    #     response = self.client.get(url)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(response.data["total_students"], 1)
