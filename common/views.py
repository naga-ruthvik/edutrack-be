from django.shortcuts import render

# Create your views here.

# a common mixin for filtering users from specific institution
class InstitutionFilterMixin:
    def get_queryset(self):
        queryset=super().get_queryset()
        institution=self.request.user.profile.institution
        return queryset.filter(institution=institution)
