from customers.models import Institution, Domain

# 1. Create the Public Tenant
# The public tenant is where the generic/landing page lives.
# schema_name must be 'public' for django-tenants.
try:
    public_tenant = Institution.objects.get(schema_name='public')
    print("Public tenant already exists.")
except Institution.DoesNotExist:
    public_tenant = Institution(
        schema_name='public',
        name='EduTrack Public',
        # Add other optional fields if necessary, e.g. logo, etc.
    )
    public_tenant.save()
    print("Created public tenant.")

# 2. Add the Domain for the Public Tenant
# Usually 'localhost' for local dev, or the actual domain in prod.
domain_url = 'localhost' # or '127.0.0.1' depending on how you access it. 
# django-tenants matches the request host to this.

try:
    domain = Domain.objects.get(domain=domain_url)
    print(f"Domain {domain_url} already exists.")
except Domain.DoesNotExist:
    domain = Domain(
        domain=domain_url,
        tenant=public_tenant,
        is_primary=True
    )
    domain.save()
    print(f"Created domain {domain_url} for public tenant.")

# Add 127.0.0.1 as well just in case
domain_url_ip = '127.0.0.1'
try:
    domain = Domain.objects.get(domain=domain_url_ip)
    print(f"Domain {domain_url_ip} already exists.")
except Domain.DoesNotExist:
    domain = Domain(
        domain=domain_url_ip,
        tenant=public_tenant,
        is_primary=False
    )
    domain.save()
    print(f"Created domain {domain_url_ip} for public tenant.")
