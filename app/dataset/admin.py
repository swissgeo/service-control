from typing import Any

from django.conf import settings
from django.contrib import admin, messages
from django.db.models import OuterRef, QuerySet, StringAgg, Subquery, Value
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from organization.models import Organization
from utils.admin import HarvestWarningMixin, HideFieldsetsOnAddMixin

from .models import Dataset, DatasetToContact, DatasetToDataset, DatasetToUnit


class DatasetToDatasetInline(admin.TabularInline):
    model = DatasetToDataset
    fk_name = "object"
    extra = 0
    autocomplete_fields = ("subject",)


class DatasetToUnitInline(admin.TabularInline):
    model = DatasetToUnit
    extra = 0
    autocomplete_fields = ("unit",)


class DatasetToContactInline(admin.TabularInline):
    model = DatasetToContact
    extra = 0
    autocomplete_fields = ("contact",)


class PublishedNonPublished(admin.SimpleListFilter):
    title = "Published / Non published Status"
    parameter_name = "custom_type"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:  # noqa: ARG002
        return [("published", "Published"), ("non_published", "Non Published")]

    def queryset(self, request: HttpRequest, queryset: QuerySet[Dataset]) -> QuerySet[Dataset]:
        if self.value() == "published":
            return queryset.filter(status__in=[Dataset.Status.PUBLISHED])
        if self.value() == "non_published":
            return queryset.exclude(status__in=[Dataset.Status.PUBLISHED])
        return queryset


class OwnerOrganizationFilter(admin.SimpleListFilter):
    """Filters datasets by the organization of the units having the owner role."""

    title = "Owner Organization"
    parameter_name = "owner_organization"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:  # noqa: ARG002
        # Only list organizations that actually own datasets
        organizations = (
            Organization.objects.filter(unit__dataset_units__role=DatasetToUnit.Role.OWNER)
            .distinct()
            .order_by("abbreviation_de")
        )
        return [(str(org.pk), f"{org.abbreviation_de}") for org in organizations]

    def queryset(self, request: HttpRequest, queryset: QuerySet[Dataset]) -> QuerySet[Dataset]:
        if self.value():
            # Subquery instead of a join, to avoid duplicates when an organization owns a dataset
            # via several units
            owned = DatasetToUnit.objects.filter(
                role=DatasetToUnit.Role.OWNER, unit__organization_id=self.value()
            ).values("dataset_id")
            return queryset.filter(pk__in=owned)
        return queryset


@admin.register(Dataset)
class DatasetAdmin(HarvestWarningMixin, HideFieldsetsOnAddMixin, admin.ModelAdmin):
    """Admin View for Dataset"""

    list_display = ("sgid", "dataset_id", "title_de", "owner", "data_source", "status")
    list_filter = ("data_source", PublishedNonPublished, OwnerOrganizationFilter)
    readonly_fields = (
        "sgid",
        "owner_organization",
        "created_at",
        "updated_at",
        "dataset_list",
        "oar_preview",
    )
    search_fields = ("sgid", "dataset_id", "title_de", "title_short_de")
    filter_horizontal = ("concepts",)
    inlines = (
        DatasetToDatasetInline,
        DatasetToUnitInline,
        DatasetToContactInline,
    )
    actions = ("set_status_draft", "set_status_published")
    save_on_top = True
    hidden_fieldsets_on_add = ("Relations", "Metadata", "Export")
    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    ("sgid", "dataset_id"),
                    "owner_organization",
                    "status",
                    ("data_source", "data_source_ids"),
                    "geocat_id",
                ),
            },
        ),
        (
            "Export",
            {
                "fields": ("oar_preview",),
            },
        ),
        (
            "Titles",
            {
                "description": "Title and short title per language.",
                "fields": (
                    ("title_de", "title_short_de"),
                    ("title_fr", "title_short_fr"),
                    ("title_en", "title_short_en"),
                    ("title_it", "title_short_it"),
                    ("title_rm", "title_short_rm"),
                ),
            },
        ),
        (
            "Descriptions",
            {
                "classes": ("wide",),
                "fields": (
                    "description_de",
                    "description_fr",
                    "description_en",
                    "description_it",
                    "description_rm",
                ),
            },
        ),
        (
            "Search",
            {
                "classes": ("collapse",),
                "fields": (
                    "additional_search_text_de",
                    "additional_search_text_fr",
                    "additional_search_text_en",
                    "additional_search_text_it",
                    "additional_search_text_rm",
                ),
            },
        ),
        (
            "Classification & attribution",
            {"fields": ("concepts", "attribution", "preferred_distribution")},
        ),
        (
            "Relations",
            {
                "classes": ("collapse",),
                "description": "Datasets in which this dataset is the subject of a relation.",
                "fields": ("dataset_list",),
            },
        ),
        (
            "Legacy",
            {
                "classes": ("collapse",),
                "fields": (
                    "legacy_contacts",
                    "legacy_part_info_url_de",
                    "legacy_part_info_url_fr",
                    "legacy_part_info_url_it",
                ),
            },
        ),
        (
            "Metadata",
            {"classes": ("collapse",), "fields": ("created_at", "updated_at")},
        ),
    )

    def _set_status(
        self, request: HttpRequest, queryset: QuerySet[Dataset], status: Dataset.Status
    ) -> None:
        # Use update() for efficiency; auto_now is not applied by update(), so set it explicitly
        updated = queryset.exclude(status=status).update(status=status, updated_at=timezone.now())
        self.message_user(
            request,
            f"{updated} dataset(s) set to status '{status.label}'.",
            messages.SUCCESS,
        )

    @admin.action(description="Transition selected datasets to Draft")
    def set_status_draft(self, request: HttpRequest, queryset: QuerySet[Dataset]) -> None:
        self._set_status(request, queryset, Dataset.Status.DRAFT)

    @admin.action(description="Transition selected datasets to Published")
    def set_status_published(self, request: HttpRequest, queryset: QuerySet[Dataset]) -> None:
        self._set_status(request, queryset, Dataset.Status.PUBLISHED)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Dataset]:
        # Annotate the German abbreviations of the owner organizations for the list view (in a
        # subquery, so that the main query is neither multiplied nor grouped)
        owners = (
            DatasetToUnit.objects.filter(dataset=OuterRef("pk"), role=DatasetToUnit.Role.OWNER)
            .values("dataset")
            .annotate(
                abbreviations=StringAgg(
                    "unit__organization__abbreviation_de",
                    delimiter=Value(", "),
                    distinct=True,
                    order_by="unit__organization__abbreviation_de",
                )
            )
            .values("abbreviations")
        )
        return super().get_queryset(request).annotate(owner_abbreviations=Subquery(owners))

    @admin.display(description="Owner", ordering="owner_abbreviations")
    def owner(self, obj: Dataset) -> str | None:
        return obj.owner_abbreviations  # ty: ignore[unresolved-attribute]

    @admin.display(description="Owner Organization")
    def owner_organization(self, obj: Dataset) -> str:
        organizations = (
            Organization.objects.filter(
                unit__dataset_units__dataset=obj,
                unit__dataset_units__role=DatasetToUnit.Role.OWNER,
            )
            .distinct()
            .order_by("name_en")
        )
        if not organizations:
            return self.get_empty_value_display()
        return format_html_join(
            ", ",
            '<a href="{}">{}</a>',
            (
                (reverse("admin:organization_organization_change", args=[org.pk]), org.name_en)
                for org in organizations
            ),
        )

    @admin.display(description="Link to OAR Record from last export")
    def oar_preview(self, obj: Dataset) -> str:
        host = (
            f"{settings.APP_ENV}.sgdi.tech" if settings.APP_ENV in ("dev", "int") else "swissgeo.ch"
        )
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            f"https://services.{host}/api/oar/rc1/collections/swissgeo-catalog/items/{obj.sgid}",
            f"Preview Dataset '{obj.sgid}' in OAR API",
        )

    @admin.display(description="Reverse Dataset Relations")
    def dataset_list(self, obj: Dataset) -> str:
        return format_html_join(
            "\n",
            '<a href="{}">{}</a><br>',
            (
                (
                    reverse("admin:dataset_dataset_change", args=[relation.object_id]),
                    str(relation),
                )
                for relation in obj.dataset_relations_as_subject.all()  # ty: ignore[unresolved-attribute]
            ),
        )

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> tuple[str, ...]:
        if obj:
            # Dataset id cannot be updated
            # TODO: depending on how we handle identifiers, we might want implement auto-generation
            # for identifiers (probably preferrable than making it readonly in edit)
            return ("sgid", "dataset_id", *self.readonly_fields)
        return tuple(self.readonly_fields)
