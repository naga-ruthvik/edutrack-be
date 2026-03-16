from customers.models import Institution, Domain

# 1. Create the Public Tenant
# The public tenant is where the generic/landing page lives.
# schema_name must be 'public' for django-tenants.
try:
    public_tenant = Institution.objects.get(schema_name="public")
    print("Public tenant already exists.")
except Institution.DoesNotExist:
    public_tenant = Institution(
        schema_name="public",
        name="EduTrack Public",
    )
    public_tenant.save()
    print("Created public tenant.")

# 2. Add Domain for the Public Tenant
# For subdomain-based tenancy, the public tenant maps to the bare domain.
# In local dev: 'localhost'
# In production: 'edutrack.com' (or your actual domain)

domain_url = "localhost"
try:
    domain = Domain.objects.get(domain=domain_url)
    print(f"Domain {domain_url} already exists.")
except Domain.DoesNotExist:
    domain = Domain(domain=domain_url, tenant=public_tenant, is_primary=True)
    domain.save()
    print(f"Created domain {domain_url} for public tenant.")

# Add 127.0.0.1 as well just in case
domain_url_ip = "127.0.0.1"
try:
    domain = Domain.objects.get(domain=domain_url_ip)
    print(f"Domain {domain_url_ip} already exists.")
except Domain.DoesNotExist:
    domain = Domain(domain=domain_url_ip, tenant=public_tenant, is_primary=False)
    domain.save()
    print(f"Created domain {domain_url_ip} for public tenant.")

print("\n--- Public tenant setup complete ---")
print("Public tenant routes:  http://localhost:8000/public/institution/")
print("Tenant routes example: http://<tenant>.localhost:8000/auth/")
print("  (Create tenant domains like 'mlritm.localhost' in the Domain table)")
