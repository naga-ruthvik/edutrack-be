import logging

from celery import shared_task
from achievements.certificate_verification.backend_interface import verify_certificate

logger = logging.getLogger(__name__)
from .models import Certificate
from .models import Skill
from django_tenants.utils import schema_context


@shared_task
def process_certificate_verification(file_path, certificate_id, schema_name="public"):
    """
    Background task to verify a certificate.
    """
    try:
        # Wrap execution in the tenant's schema context
        with schema_context(schema_name):
            # Run verification
            # verify_certificate accepts a file path string
            result = verify_certificate(file_path)

            # Update your model with results
            cert = Certificate.objects.get(id=certificate_id)
            final_verdict = result["unified_output"]["status"]
            if final_verdict == "verified":
                cert.status = Certificate.Status.AI_VERIFIED
            else:
                cert.status = Certificate.Status.NEEDS_REVIEW
            cert.title = result["unified_output"]["title"]
            cert.issuing_organization = result["unified_output"]["issuing_organization"]
            cert.verification_url = result["unified_output"]["verification_url"]
            cert.category = result["unified_output"]["category"]
            cert.level = result["unified_output"]["level"]
            cert.rank = result["unified_output"]["rank"]
            # Parse date if possible
            date_str = result["unified_output"]["date_of_event"]
            parsed_date = None
            if date_str:
                from dateutil import parser as date_parser

                try:
                    parsed_date = date_parser.parse(date_str).date()
                except (ValueError, TypeError):
                    parsed_date = None
            cert.date_of_event = parsed_date
            cert.academic_year = result["unified_output"]["academic_year"] or ""
            cert.ai_summary = result["unified_output"]["ai_summary"]
            cert.reason = result["unified_output"].get("reason")

            # Save rejection reason if present
            if result.get("unified_output", {}).get("rejection_reason"):
                # You might want to save this to a field, e.g., verification_reason
                # Ensure you have a field for this in your model if you want to store it
                result["rejection_reason"] = result["unified_output"][
                    "rejection_reason"
                ]

            skills = result["unified_output"]["skills"]
            for skill_name in skills:
                try:
                    # Get or create skill, handling case insensitivity preferred
                    skill_obj, _ = Skill.objects.get_or_create(name=skill_name.lower())
                except Exception:
                    # Handle race condition or IntegrityError
                    try:
                        skill_obj = Skill.objects.get(name=skill_name.lower())
                    except Skill.DoesNotExist:
                        # Should not happen if get_or_create failed due to integrity error
                        # but safe fallback
                        continue

                cert.secondary_skills.add(skill_obj)

            cert.save()
            return result

    except Exception as e:
        logger.exception("Certificate verification failed for id=%s", certificate_id)
        return {"error": str(e)}
