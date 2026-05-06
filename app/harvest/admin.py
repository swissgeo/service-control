from django.contrib import admin

from harvest.models import DatasetToContactMapping, DatasetToUnitMapping, OrganizationMapping


@admin.register(OrganizationMapping)
class OrganizationMappingAdmin(admin.ModelAdmin):
    """Admin View for OrganizationMapping"""

    list_display = ("provider_id_prefix", "organization_id", "update_organization")


@admin.register(DatasetToUnitMapping)
class DatasetToUnitMappingAdmin(admin.ModelAdmin):
    """Admin View for DatasetToUnitMapping"""

    list_display = ("dataset_id_prefix", "organization_id", "unit_id")


@admin.register(DatasetToContactMapping)
class DatasetToContactMappingAdmin(admin.ModelAdmin):
    """Admin View for DatasetToUnitMapping"""

    list_display = ("dataset_id_prefix", "role", "organization_id", "contact_name_en")
