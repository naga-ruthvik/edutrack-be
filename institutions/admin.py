from django.contrib import admin

# Register your models here.
from .models import Institution, Department
admin.site.register(Institution)
admin.site.register(Department)
