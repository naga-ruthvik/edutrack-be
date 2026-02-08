from django.urls import path
from .views import sync_data

urlpatterns = [
    path('sync-data/', sync_data, name='sync_data'),
]
