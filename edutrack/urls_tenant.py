# edutrack/urls_tenant.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from djoser.views import UserViewSet

urlpatterns = [
    # --- 0. PUBLIC & ADMIN (Shared) ---
    path("public/", include("public_api.urls")),
    path("admin/", admin.site.urls),
    # --- 1. TENANT ROOT (Swagger UI) ---
    path(
        "swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="tenant-root",
    ),
    # --- 2. AUTHENTICATION (Djoser + Session Login) ---
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    path("api-auth/", include("rest_framework.urls")),  # Login/Logout for browsable API
    path(
        "activate/<str:uid>/<str:token>/",
        UserViewSet.as_view({"get": "activation"}),
        name="activation",
    ),
    # --- 3. DOCUMENTATION ---
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"
    ),
    # --- 4. TENANT APPS ---
    path("users/", include("authentication.urls")),
    path("administration/", include("academics.urls")),
    path("achievements/", include("achievements.urls")),
    path("resume/", include("resume.urls")),
    path("profiles/", include("profiles.urls")),
    path("erp/", include("erp.urls")),
]
