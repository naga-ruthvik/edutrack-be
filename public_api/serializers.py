from rest_framework import serializers
from customers.models import Institution, Domain

class RegisterCollegeSerializer(serializers.Serializer):
    """
    Serializer to validate input for creating a new College Tenant.
    """
    college_name = serializers.CharField(max_length=100)
    slug = serializers.SlugField(max_length=50, help_text="Unique identifier (e.g. 'vardhaman')")
    admin_email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, 
        style={'input_type': 'password'}, # This makes it a password box in HTML
        min_length=8
    )

    def validate_slug(self, value):
        """
        Check if this slug (schema_name) is already taken.
        """
        if Institution.objects.filter(schema_name=value).exists():
            raise serializers.ValidationError("This college identifier (slug) is already registered.")
        return value.lower()

class InstitutionSerializer(serializers.ModelSerializer):
    """
    Serializer for Institution model.
    """
    domain = serializers.SerializerMethodField()
    
    class Meta:
        model = Institution
        fields = ['id', 'name', 'schema_name', 'domain']
    
    def get_domain(self, obj):
        """
        Get the primary domain for this institution.
        Query Domain model directly since DomainMixin doesn't provide predictable reverse relation.
        """
        primary_domain = Domain.objects.filter(tenant=obj, is_primary=True).first()
        return primary_domain.domain if primary_domain else None