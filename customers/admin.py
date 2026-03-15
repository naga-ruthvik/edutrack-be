from django.contrib import admin

# Register your models here.
from .models import Institution, Domain

admin.site.register(Institution)
admin.site.register(Domain)
