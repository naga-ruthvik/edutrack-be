# edutrack/urls_public.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("public/", include("public_api.urls")),
    path("orbit/", include("orbit.urls")),
]
