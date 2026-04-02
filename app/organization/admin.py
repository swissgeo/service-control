from typing import TYPE_CHECKING, Any

from django.contrib import admin

from .models import Organization, Unit

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http.request import HttpRequest


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
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

    def delete_queryset(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        queryset: QuerySet[Organization],
    ) -> None:
        #  Make sure that the cognito group is deleted when batch deleting a organizations
        for obj in queryset:
            obj.delete()


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    """Admin View for Organization Unit"""

    list_display = ("unit_id", "name_en", "get_organization_name")
    readonly_fields = ("created", "updated")
    list_filter = ("organization",)

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

    def delete_queryset(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        queryset: QuerySet[Unit],
    ) -> None:
        #  Make sure that the cognito group is deleted when batch deleting a units
        for obj in queryset:
            obj.delete()
