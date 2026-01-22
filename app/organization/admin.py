from typing import Any

from django.contrib import admin
from django.http.request import HttpRequest

from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):  # type:ignore[type-arg]
    """Admin View for Organization"""

    list_display = ("organization_id", "acronym_en", "name_en")
    readonly_fields = ("created", "updated")

    def get_readonly_fields(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Organization id cannot be updated
            return (*self.readonly_fields, "organization_id")
        return self.readonly_fields
