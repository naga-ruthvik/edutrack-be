from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

# 1. Rename 'Client' to 'Institution'
class Institution(TenantMixin):
    """
    This is the Root Entity. 
    It handles BOTH the Multi-Tenant logic (schema creation)
    AND the Business logic (Address, Logo, Contact).
    """
    
    # --- System Fields (Required by django-tenants) ---
    name = models.CharField(max_length=100, unique=True) # e.g. "Vardhaman College"
    auto_create_schema = True 

    # --- Your Custom Fields (Merged here) ---
    logo = models.ImageField(upload_to='institution_logos/', null=True, blank=True)
    contact = models.CharField(max_length=20, null=True, blank=True)
    
    # Address Block
    street = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=200, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Domain(DomainMixin):
    pass