from django.urls import path
from .views import InstitutionsGenericView

urlpatterns = [
    path("institution/", InstitutionsGenericView.as_view(), name="institution_views"),
]
