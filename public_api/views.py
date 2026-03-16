from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django_tenants.utils import schema_context
from djoser.email import ActivationEmail
from django.db import IntegrityError

# Models
from customers.models import Institution, Domain
from authentication.models import User

from .serializers import InstitutionCreateSerializer, InstitutionListSerializer


from django.db import transaction, IntegrityError
from rest_framework.permissions import AllowAny
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status


import logging
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class InstitutionsGenericView(GenericAPIView):
    """
    Public Endpoint: Creates a new College (Tenant) AND the Principal (Admin User).
    URL: /public/institution/
    """

    queryset = Institution.objects.all()
    permission_classes = []

    def get_serializer_class(self):
        if self.request.method == "POST":
            return InstitutionCreateSerializer
        return InstitutionListSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        college_name = data["college_name"]
        slug = data["slug"]
        admin_email = data["admin_email"]
        password = data["password"]

        try:
            with transaction.atomic():
                institution = self._create_institution(
                    schema_name=slug, name=college_name
                )

                self._create_domain(domain=slug, institution=institution)

                user = self._create_admin_user(
                    schema_name=institution.schema_name,
                    email=admin_email,
                    username=admin_email,
                    password=password,
                )

        except IntegrityError as e:
            logger.warning(
                f"IntegrityError during registration for slug '{slug}': {str(e)}"
            )
            return Response(
                {"error": "A college with this identifier already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        except ValidationError as e:
            logger.warning(f"ValidationError during registration: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.exception(
                f"Unexpected error during college registration for slug '{slug}'"
            )
            return Response(
                {"error": "Registration failed. Please try again or contact support."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        email_sent = self._send_activation_email(user)

        message = f"College '{college_name}' created successfully."
        if email_sent:
            message += f" Activation email sent to {admin_email}."
        else:
            message += " However, activation email failed. Please contact support."

        return Response(
            {
                "message": message,
                "login_url": f"/api/{slug}/auth/jwt/create/",
            },
            status=status.HTTP_201_CREATED,
        )

    def get(self, request):
        institutions = self.get_queryset()
        serialized_data = self.get_serializer(institutions, many=True)
        return Response(serialized_data.data, status=status.HTTP_200_OK)

    # ---------------- PRIVATE METHODS ---------------- #

    def _create_institution(self, schema_name, name):
        return Institution.objects.create(schema_name=schema_name, name=name)

    def _create_domain(self, domain, institution):
        return Domain.objects.create(domain=domain, tenant=institution, is_primary=True)

    def _create_admin_user(self, schema_name, email, username, password):
        with schema_context(schema_name):
            return User.objects.create_user(
                email=email,
                username=username,
                password=password,
                role=User.Role.ADMIN,
                is_staff=True,
                is_superuser=True,
                is_active=False,
            )

    def _send_activation_email(self, user):
        """Returns True if email sent successfully"""
        try:
            context = {"user": user}
            email = ActivationEmail(context=context)
            email.send([user.email])
            return True
        except Exception as e:
            logger.error(f"Failed to send activation email to {user.email}: {str(e)}")
            return False
