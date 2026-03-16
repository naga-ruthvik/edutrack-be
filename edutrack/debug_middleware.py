# edutrack/debug_middleware.py
from django_tenants.middleware.main import TenantMainMiddleware
import logging

logger = logging.getLogger(__name__)


class DebugTenantMiddleware(TenantMainMiddleware):
    """
    Debug wrapper around TenantMainMiddleware to log tenant lookup behavior.
    Uses subdomain-based tenant resolution.
    """

    def process_request(self, request):
        """Override to log URLConf switching"""
        # Call parent to set tenant and URLConf
        result = super().process_request(request)

        # Log concise info
        tenant_name = (
            request.tenant.schema_name if hasattr(request, "tenant") else "NO TENANT"
        )
        urlconf = getattr(request, "urlconf", "NOT SET")

        logger.info(
            f"[TENANT] {tenant_name:15} | urlconf={urlconf} | {request.method:4} {request.path}"
        )

        return result
