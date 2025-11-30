import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edutrack.settings')
django.setup()

from customers.models import Institution, Domain

print("=== FIXING TENANT CONFIGURATION ===\n")

# Delete all incorrect domains
print("Deleting all existing domains...")
Domain.objects.all().delete()

# Delete public tenant if it exists
try:
    public_tenant = Institution.objects.get(schema_name='public')
    if public_tenant.name in ['Public Tenant', 'public']:
        print(f"Deleting public tenant: {public_tenant.name}")
        public_tenant.delete()
except Institution.DoesNotExist:
    print("No public tenant to delete")

# Ensure vmeg tenant exists
tenant, created = Institution.objects.get_or_create(
    schema_name='vmeg',
    defaults={'name': 'VMEG College'}
)
if created:
    print(f"✅ Created tenant: {tenant.schema_name} - {tenant.name}")
else:
    print(f"✅ Tenant already exists: {tenant.schema_name} - {tenant.name}")

# Create correct domain
domain = Domain(domain='vmeg', tenant=tenant, is_primary=True)
domain.save()
print(f"✅ Created domain: '{domain.domain}' -> tenant: '{tenant.schema_name}'")

print("\n=== VERIFICATION ===")
print("\nTenants:")
for t in Institution.objects.all():
    print(f"  - Schema: '{t.schema_name}' | Name: '{t.name}'")

print("\nDomains:")
for d in Domain.objects.all():
    print(f"  - Domain: '{d.domain}' -> Tenant: '{d.tenant.schema_name}' (Primary: {d.is_primary})")

print("\n✅ Done! Now restart your server and access: http://127.0.0.1:8000/api/vmeg/")
