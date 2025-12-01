from django.contrib import admin

from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):  # type:ignore[type-arg]
    '''Admin View for Organization'''

    list_display = ('organization_id', 'acronym_en', 'name_en')
    readonly_fields = ('created', 'updated')
