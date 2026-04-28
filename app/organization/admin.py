from typing import Any

from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.html import format_html_join

from .models import Contact, Organization, Unit


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin View for Organization"""

    list_display = ("organization_id", "acronym_en", "name_en")
    readonly_fields = ("created", "updated")

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Organization id cannot be updated
            return (*self.readonly_fields, "organization_id")
        return self.readonly_fields

    def delete_queryset(
        self,
        request: HttpRequest,
        queryset: QuerySet[Organization],
    ) -> None:
        #  Make sure that the cognito group is deleted when batch deleting a organizations
        for obj in queryset:
            obj.delete()


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    """Admin View for Organization Unit"""

    list_display = ("unit_id", "name_en", "get_organization_name", "number_of_datasets")
    list_filter = ("organization",)
    readonly_fields = ("created", "updated", "dataset_list")

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Organization id cannot be updated
            return (*self.readonly_fields, "unit_id", "organization")
        return self.readonly_fields

    @admin.display(description="Organization", ordering="organization__name_en")
    def get_organization_name(self, obj: Unit) -> str:
        return obj.organization.name_en

    @admin.display(description="Number of Datasets")
    def number_of_datasets(self, obj: Contact) -> int:
        return obj.number_of_datasets  # type:ignore[unresolved-attribute]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Unit]:
        qs = super().get_queryset(request)
        return qs.annotate(number_of_datasets=Count("datasets"))

    @admin.display(description="Datasets")
    def dataset_list(self, obj: Unit) -> str:
        # For performance reasons, related datasets are not shown inline
        return format_html_join(
            "\n",
            '<a href="{}">{}</a><br>',
            (
                (
                    reverse("admin:dataset_dataset_change", args=[dataset.pk]),
                    str(dataset),
                )
                for dataset in obj.datasets.order_by("dataset_id").all()  # type:ignore[unresolved-attribute]
            ),
        )

    def delete_queryset(
        self,
        request: HttpRequest,
        queryset: QuerySet[Unit],
    ) -> None:
        #  Make sure that the cognito group is deleted when batch deleting a units
        for obj in queryset:
            obj.delete()


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Admin View for Organization Contact"""

    list_display = ("organization", "name_en", "number_of_datasets")
    list_filter = ("organization",)
    readonly_fields = ("created", "updated", "dataset_list")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Contact]:
        qs = super().get_queryset(request)
        return qs.annotate(number_of_datasets=Count("datasets"))

    @admin.display(description="Number of Datasets")
    def number_of_datasets(self, obj: Contact) -> int:
        return obj.number_of_datasets  # type:ignore[unresolved-attribute]

    @admin.display(description="Datasets")
    def dataset_list(self, obj: Contact) -> str:
        # For performance reasons, related datasets are not shown inline
        return format_html_join(
            "\n",
            '<a href="{}">{}</a><br>',
            (
                (
                    reverse("admin:dataset_dataset_change", args=[dataset.pk]),
                    str(dataset),
                )
                for dataset in obj.datasets.order_by("dataset_id").all()  # type:ignore[unresolved-attribute]
            ),
        )
