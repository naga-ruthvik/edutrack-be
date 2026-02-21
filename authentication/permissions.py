from rest_framework import permissions
from authentication.models import User


class IsInstitutionAdmin(permissions.BasePermission):
    message = "You must be an Institution Admin to perform this action."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role == User.Role.ADMIN


class IsFaculty(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.FACULTY


class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.STUDENT


class IsStudentOrFaculty(permissions.BasePermission):
    """
    Allows access to users who are either a Student OR a Faculty member.
    (DRF permission_classes uses AND logic, so this combines two roles in one class.)
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role in (User.Role.STUDENT, User.Role.FACULTY)
