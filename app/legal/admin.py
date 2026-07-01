from django.contrib import admin

from legal.models import GeopoliticalEntity


@admin.register(GeopoliticalEntity)
class OrganizationMappingAdmin(admin.ModelAdmin):
    """Admin View for Geopolicitcal Entity"""

    list_display = ("geopolitical_entity_id", "type", "name")
