from rest_framework.permissions import BasePermission

class IsInstitutuionAdmin(BasePermission):
    message="you need to login/ you are not admin to view"
    def has_permission(self, request, view):
        return getattr(request.user.profile, 'role', None) == 'ADMIN'

class IsHod(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user.profile, 'role', None) == 'HOD'
    
class IsFaculty(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user.profile, 'role', None) == 'FACULTY'

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user.profile, 'role', None) == 'STUDENT'