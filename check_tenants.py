import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edutrack.settings')
django.setup()

from customers.models import Institution, Domain

print("=== TENANTS ===")
tenants = Institution.objects.all()
print(f"Found {tenants.count()} tenant(s)")
for t in tenants:
    print(f"  - Schema: '{t.schema_name}' | Name: '{t.name}'")

print("\n=== DOMAINS ===")
domains = Domain.objects.all()
print(f"Found {domains.count()} domain(s)")
for d in domains:
    print(f"  - Domain: '{d.domain}' | Tenant: '{d.tenant.schema_name}' | Primary: {d.is_primary}")
