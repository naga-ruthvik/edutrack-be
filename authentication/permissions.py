from rest_framework import permissions

class IsInstitutionAdmin(permissions.BasePermission):
    message = "You must be an Institution Admin to perform this action."
    
    def has_permission(self, request, view):
        # 1. Check Auth
        if not request.user.is_authenticated:
            return False
        # 2. Check Role (Directly on User model now)
        return request.user.role == 'ADMIN'

class IsFaculty(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'FACULTY'

class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'STUDENT'

class IsRecruiter(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'RECRUITER'