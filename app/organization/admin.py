from typing import Any

from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.html import format_html_join

from utils.admin import HarvestWarningMixin, HideFieldsetsOnAddMixin

from .models import Attribution, Contact, Organization, Unit


class AttributionInline(admin.TabularInline):  # type:ignore[type-arg]
    """Read-only list of the attributions linked to a provider"""

    model = Attribution
    fields = ("attribution_id", "abbreviation_en", "name_en", "url_en")
    readonly_fields = fields
    show_change_link = True
    extra = 0
    can_delete = False


@admin.register(Organization)
class OrganizationAdmin(HarvestWarningMixin, HideFieldsetsOnAddMixin, admin.ModelAdmin):
    """Admin View for Organization"""

    save_on_top = True
    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    ("sgid", "organization_id"),
                    ("data_source", "data_source_ids"),
                    "geopolitical_entity",
                ),
            },
        ),
        (
            "Names",
            {
                "description": "Name and abbreviation per language.",
                "fields": (
                    ("name_de", "abbreviation_de"),
                    ("name_fr", "abbreviation_fr"),
                    ("name_en", "abbreviation_en"),
                    ("name_it", "abbreviation_it"),
                    ("name_rm", "abbreviation_rm"),
                ),
            },
        ),
        ("Permissions", {"classes": ("collapse",), "fields": ("vp_org_admin_policy_id",)}),
        ("Metadata", {"classes": ("collapse",), "fields": ("created", "updated")}),
    )

    list_display = ("organization_id", "abbreviation_en", "name_en", "data_source")
    list_filter = ("data_source",)
    readonly_fields = ("sgid", "created", "updated")
    search_fields = (
        "sgid",
        "organization_id",
        "abbreviation_en",
        "name_en",
        "abbreviation_de",
        "name_de",
    )
    inlines = (AttributionInline,)

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Organization id cannot be updated
            return (*self.readonly_fields, "sgid", "organization_id")
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
class UnitAdmin(HideFieldsetsOnAddMixin, admin.ModelAdmin):
    """Admin View for Organization Unit"""

    save_on_top = True
    hidden_fieldsets_on_add = ("Datasets", "Metadata")
    fieldsets = (
        ("Identification", {"fields": ("organization", "unit_id")}),
        ("Names", {"fields": ("name_de", "name_fr", "name_en", "name_it", "name_rm")}),
        (
            "Permissions",
            {
                "classes": ("collapse",),
                "fields": ("vp_dataset_admin_policy_id", "vp_dataset_contributor_policy_id"),
            },
        ),
        ("Datasets", {"classes": ("collapse",), "fields": ("dataset_list",)}),
        ("Metadata", {"classes": ("collapse",), "fields": ("created", "updated")}),
    )

    list_display = ("unit_id", "name_en", "get_organization_name", "number_of_datasets")
    list_filter = ("organization",)
    readonly_fields = ("created", "updated", "dataset_list")
    search_fields = (
        "unit_id",
        "name_en",
        "name_de",
        "organization__organization_id",
        "organization__name_en",
        "organization__name_de",
    )

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
        return obj.number_of_datasets  # ty: ignore[unresolved-attribute]

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
                for dataset in obj.datasets.order_by("dataset_id").all()  # ty: ignore[unresolved-attribute]
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
class ContactAdmin(HideFieldsetsOnAddMixin, admin.ModelAdmin):
    """Admin View for Organization Contact"""

    save_on_top = True
    hidden_fieldsets_on_add = ("Datasets", "Metadata")
    fieldsets = (
        (
            "Identification",
            {"fields": ("organization", ("data_source", "data_source_ids"))},
        ),
        ("Names", {"fields": ("name_de", "name_fr", "name_en", "name_it", "name_rm")}),
        (
            "Contact details",
            {
                "fields": (
                    "emails",
                    "phone",
                    "url_de",
                    "url_fr",
                    "url_en",
                    "url_it",
                    "url_rm",
                ),
            },
        ),
        (
            "Address",
            {
                "fields": (
                    "address_delivery_point",
                    ("address_postal_code", "address_city"),
                    "address_administrative_area",
                    "address_country",
                ),
            },
        ),
        ("Legacy", {"classes": ("collapse",), "fields": ("legacy_contact",)}),
        ("Datasets", {"classes": ("collapse",), "fields": ("dataset_list",)}),
        ("Metadata", {"classes": ("collapse",), "fields": ("created", "updated")}),
    )

    list_display = ("organization", "name_en", "number_of_datasets")
    list_filter = ("organization",)
    readonly_fields = ("created", "updated", "dataset_list")
    search_fields = (
        "name_en",
        "name_de",
        "organization__organization_id",
        "organization__name_en",
        "organization__name_de",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Contact]:
        qs = super().get_queryset(request)
        return qs.annotate(number_of_datasets=Count("datasets"))

    @admin.display(description="Number of Datasets")
    def number_of_datasets(self, obj: Contact) -> int:
        return obj.number_of_datasets  # ty: ignore[unresolved-attribute]

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
                for dataset in obj.datasets.order_by("dataset_id").all()  # ty: ignore[unresolved-attribute]
            ),
        )


@admin.register(Attribution)
class AttributionAdmin(HarvestWarningMixin, HideFieldsetsOnAddMixin, admin.ModelAdmin):
    """Admin View for Organization Attribution"""

    save_on_top = True
    hidden_fieldsets_on_add = ("Datasets", "Metadata")
    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    "attribution_id",
                    "organization",
                    ("data_source", "data_source_ids"),
                ),
            },
        ),
        (
            "Names",
            {
                "description": "Name and abbreviation per language.",
                "fields": (
                    ("name_de", "abbreviation_de"),
                    ("name_fr", "abbreviation_fr"),
                    ("name_en", "abbreviation_en"),
                    ("name_it", "abbreviation_it"),
                    ("name_rm", "abbreviation_rm"),
                ),
            },
        ),
        ("URLs", {"fields": ("url_de", "url_fr", "url_en", "url_it", "url_rm")}),
        ("Datasets", {"classes": ("collapse",), "fields": ("dataset_list",)}),
        ("Metadata", {"classes": ("collapse",), "fields": ("created", "updated")}),
    )

    list_display = ("attribution_id", "abbreviation_en", "name_en", "number_of_datasets")
    list_filter = ("data_source", "organization")
    readonly_fields = ("created", "updated", "dataset_list")
    search_fields = (
        "attribution_id",
        "name_en",
        "name_de",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Attribution]:
        qs = super().get_queryset(request)
        return qs.annotate(number_of_datasets=Count("attribution_datasets"))

    @admin.display(description="Number of Datasets")
    def number_of_datasets(self, obj: Attribution) -> int:
        return obj.number_of_datasets  # ty: ignore[unresolved-attribute]

    @admin.display(description="Datasets")
    def dataset_list(self, obj: Attribution) -> str:
        # For performance reasons, related datasets are not shown inline
        return format_html_join(
            "\n",
            '<a href="{}">{}</a><br>',
            (
                (
                    reverse("admin:dataset_dataset_change", args=[dataset.pk]),
                    str(dataset),
                )
                for dataset in obj.attribution_datasets.order_by("dataset_id").all()  # ty: ignore[unresolved-attribute]
            ),
        )
