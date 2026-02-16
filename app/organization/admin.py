from typing import TYPE_CHECKING, Any

from django.contrib import admin

from .models import Organization, Unit

if TYPE_CHECKING:
    from django.http.request import HttpRequest


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


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):  # type:ignore[type-arg]
    """Admin View for Organization Unit"""

    list_display = ("unit_id", "name_en", "get_organization_name")
    readonly_fields = ("created", "updated")

    def get_readonly_fields(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Organization id cannot be updated
            return (*self.readonly_fields, "unit_id", "organization")
        return self.readonly_fields

    @admin.display(description="Organization", ordering="organization__name_en")
    def get_organization_name(self, obj: Unit) -> str:
        return obj.organization.name_en
