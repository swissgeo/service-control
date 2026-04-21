from django.contrib import admin

from harvest.models import DatasetToUnitMapping


@admin.register(DatasetToUnitMapping)
class DatasetToUnitMappingAdmin(admin.ModelAdmin):
    """Admin View for DatasetToUnitMapping"""

    list_display = ("dataset_id_prefix", "organization_id", "unit_id")
