"""
Django settings for edutrack project.
"""

from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-wqb6)$0u0_7v^11#+pjq-7sb(i5f6es6486*iovmyd@)@$62#t"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# --- APPLICATION DEFINITION ---

SHARED_APPS = (
    "django_tenants",
    "customers",  # Tenant Model
    "public_api",  # Landing Page
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",  # REQUIRED for frontend
    "authentication",
    "orbit",
)

TENANT_APPS = (
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.admin",
    "djoser",  # Auth Endpoints (Tenant specific)
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",  # API Documentation
    "authentication",
    "profiles",
    "academics",
    "achievements",
    "resume",
    "lms",
    "erp",
)

INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS
]

# --- TENANT CONFIG ---
TENANT_MODEL = "customers.Institution"
TENANT_DOMAIN_MODEL = "customers.Domain"
AUTH_USER_MODEL = "authentication.User"

# Path-based tenancy - TenantSubfolderMiddleware only uses ROOT_URLCONF
TENANT_SUBFOLDER_PREFIX = "api"
PUBLIC_SCHEMA_URLCONF = "edutrack.urls_public"
ROOT_URLCONF = (
    "edutrack.urls_tenant"  # CRITICAL: Middleware wraps this for /api/{tenant}/
)
TENANT_URLCONF = "edutrack.urls_tenant"  # Not used by TenantSubfolderMiddleware

# --- MIDDLEWARE ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    "corsheaders.middleware.CorsMiddleware",

    "whitenoise.middleware.WhiteNoiseMiddleware",

    "edutrack.debug_middleware.DebugTenantSubfolderMiddleware",

    "orbit.middleware.OrbitMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "edutrack.wsgi.application"

# --- DATABASE ---
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": "edutrack-dev",
        "USER": "postgres",
        "PASSWORD": "1234",
        "HOST": "localhost",
        "PORT": "5432",
        "CONN_MAX_AGE": None,
    }
}

DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

# --- PASSWORDS ---
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# --- INTERNATIONALIZATION ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- STATIC & MEDIA FILES ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- AWS S3 STORAGE ---
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = "ap-south-1"
AWS_S3_SIGNATURE_VERSION = "s3v4"

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "region_name": AWS_S3_REGION_NAME,
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF & AUTH ---
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=2),
    "ROTATE_REFRESH_TOKENS": False,
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# --- CORS ---
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://localhost:3000",
]

# --- DJOSER ---
DJOSER = {
    "LOGIN_FIELD": "username",
    "USER_CREATE_PASSWORD_RETYPE": True,
    "SET_PASSWORD_RETYPE": True,
    "SEND_ACTIVATION_EMAIL": True,
    "ACTIVATION_URL": "activate/{uid}/{token}",
    "PASSWORD_RESET_CONFIRM_URL": "password/reset/confirm/{uid}/{token}",
    "SERIALIZERS": {
        "current_user": "authentication.serializers.CurrentUserSerializer",
    },
}

# --- EMAIL ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")

# --- OTHER ---
SPECTACULAR_SETTINGS = {"DISABLE_ERRORS_AND_WARNINGS": True}

CELERY_BROKER_URL = "redis://localhost:6379/1"

# --- LOGGING (for debugging) ---
# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "handlers": {
#         "console": {
#             "class": "logging.StreamHandler",
#         },
#     },
#     "loggers": {
#         "edutrack.debug_middleware": {
#             "handlers": ["console"],
#             "level": "INFO",
#         },
#     },
# }

# settings.py
ORBIT_CONFIG = {
    "ENABLED": True,
    "SLOW_QUERY_THRESHOLD_MS": 500,
    "STORAGE_LIMIT": 1000,
    # Core watchers
    "RECORD_REQUESTS": True,
    "RECORD_QUERIES": True,
    "RECORD_LOGS": True,
    "RECORD_EXCEPTIONS": True,
    # Extended watchers
    "RECORD_COMMANDS": True,
    "RECORD_CACHE": True,
    "RECORD_MODELS": True,
    "RECORD_HTTP_CLIENT": True,
    "RECORD_MAIL": True,
    "RECORD_SIGNALS": True,
    # Advanced watchers (v0.5.0+)
    "RECORD_JOBS": True,
    "RECORD_REDIS": True,
    "RECORD_GATES": True,
    # v0.6.0 watchers
    "RECORD_TRANSACTIONS": True,
    "RECORD_STORAGE": True,
    # Security
    # "AUTH_CHECK": lambda request: request.user.is_staff,
    "IGNORE_PATHS": [
    r'.*/orbit/.*',
    r'^/static/.*',
    r'^/media/.*'
]

}
