# edutrack/urls_public.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # This handles http://127.0.0.1:8000/public/...
    path('public/', include('public_api.urls')),
    path('silk/', include('silk.urls', namespace='silk')),
]