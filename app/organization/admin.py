from typing import TYPE_CHECKING, Any

from asgiref.sync import async_to_sync

from django.contrib import admin

from .models import Organization, Unit

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.forms import ModelForm
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

    def save_model(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Organization,
        form: ModelForm[Organization],  # noqa: ARG002 unused argument
        change: bool,  # noqa: ARG002 unused argument
    ) -> None:
        async_to_sync(obj.save_and_sync)()

    def delete_model(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Organization,
    ) -> None:
        async_to_sync(obj.delete_and_sync)()

    def delete_queryset(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        queryset: QuerySet[Organization],
    ) -> None:
        for obj in queryset:
            async_to_sync(obj.delete_and_sync)()


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
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

    def save_model(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Unit,
        form: ModelForm[Unit],  # noqa: ARG002 unused argument
        change: bool,  # noqa: ARG002 unused argument
    ) -> None:
        async_to_sync(obj.save_and_sync)()

    def delete_model(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Unit,
    ) -> None:
        async_to_sync(obj.delete_and_sync)()

    def delete_queryset(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        queryset: QuerySet[Unit],
    ) -> None:
        for obj in queryset:
            async_to_sync(obj.delete_and_sync)()
