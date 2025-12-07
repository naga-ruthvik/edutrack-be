from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
import uuid

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

    edlink_integration_id = models.UUIDField(null=True, blank=True)
    edlink_access_token = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class Domain(DomainMixin):
    pass

class LmsEvent(models.Model):
    """
    PUBLIC SCHEMA - Edlink change events for incremental sync
    Cron monitors these → triggers tenant syncs
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Edlink event data
    integration_id = models.UUIDField(db_index=True)  # Which integration
    date = models.DateTimeField(db_index=True)
    type = models.CharField(max_length=20)  # created/updated/deleted
    target = models.CharField(max_length=50, db_index=True)  # person/course/class
    target_id = models.UUIDField()  # Specific object UUID
    
    # Which tenant
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name='events'
    )
    
    class Meta:
        db_table = 'lms_event'  # Forces public schema
        indexes = [
            models.Index(fields=['integration_id', 'date']),
            models.Index(fields=['target', 'target_id']),
            models.Index(fields=['institution', 'date']),
        ]
    
    def __str__(self):
        return f"{self.type} {self.target}:{self.target_id} ({self.institution.schema_name})"