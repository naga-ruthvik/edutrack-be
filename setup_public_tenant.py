import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edutrack.settings')
django.setup()

from customers.models import Institution, Domain

print("=== CREATING PUBLIC TENANT ===\n")

# Create or get public tenant
tenant, created = Institution.objects.get_or_create(
    schema_name='public',
    defaults={'name': 'Public Schema'}
)

if created:
    print(f"✅ Created public tenant: '{tenant.schema_name}'")
else:
    print(f"✅ Public tenant already exists: '{tenant.schema_name}'")

# Delete existing localhost/127.0.0.1 domains to avoid conflicts
Domain.objects.filter(domain__in=['localhost', '127.0.0.1']).delete()

# Create domains for public tenant
localhost_domain = Domain(domain='localhost', tenant=tenant, is_primary=True)
localhost_domain.save()
print(f"✅ Created domain: 'localhost' -> 'public' (Primary: True)")

ip_domain = Domain(domain='127.0.0.1', tenant=tenant, is_primary=False)
ip_domain.save()
print(f"✅ Created domain: '127.0.0.1' -> 'public' (Primary: False)")

print("\n=== FINAL CONFIGURATION ===")
print("\nAll Tenants:")
for t in Institution.objects.all():
    print(f"  - Schema: '{t.schema_name}' | Name: '{t.name}'")

print("\nAll Domains:")
for d in Domain.objects.all():
    print(f"  - Domain: '{d.domain}' -> Tenant: '{d.tenant.schema_name}' (Primary: {d.is_primary})")

print("\n✅ Done! You can now access:")
print("   - Public APIs: http://localhost:8000/public/ or http://127.0.0.1:8000/public/")
print("   - Tenant APIs: http://127.0.0.1:8000/api/vmeg/")
