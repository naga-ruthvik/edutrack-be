from django.shortcuts import render

# Create your views here.

# a common mixin for filtering users from specific institution
class InstitutionFilterMixin:
    def get_queryset(self):
        queryset=super().get_queryset()
        instituion=self.request.user.profile.institution
        return queryset.filter(instituion=instituion)
