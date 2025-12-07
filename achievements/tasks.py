from celery import shared_task
from achievements.certificate_verification.backend_interface import verify_certificate
import os
from pprint import pprint
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
            cert.verification_status = result["unified_output"]["status"]
            cert.title = result["unified_output"]["title"]
            cert.issuing_organization = result["unified_output"]["issuing_organization"]
            cert.verification_url = result["unified_output"]["verification_url"]
            cert.category = result["unified_output"]["category"]
            cert.level = result["unified_output"]["level"]
            cert.rank = result["unified_output"]["rank"]
            cert.date_of_event = result["unified_output"]["date_of_event"]
            cert.academic_year = result["unified_output"]["academic_year"] or ""
            cert.ai_summary = result["unified_output"]["ai_summary"]
            
            # Save rejection reason if present
            if result.get("unified_output", {}).get("rejection_reason"):
                # You might want to save this to a field, e.g., verification_reason
                # Ensure you have a field for this in your model if you want to store it
                result["rejection_reason"] = result["unified_output"]["rejection_reason"]

            skills = result["unified_output"]["skills"]
            for skill_name in skills:
                # Get or create skill, handling case insensitivity preferred
                skill_obj, _ = Skill.objects.get_or_create(name=skill_name.lower())
                cert.secondary_skills.add(skill_obj)
                
            cert.verification_data = result
            cert.save()
            return result
            
    except Exception as e:
        pprint(e)
        return {"error": str(e)}