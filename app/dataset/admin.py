from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.html import format_html_join

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
        return [("published", "Published"),("non_published", "Non Published")]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Dataset]
    ) -> QuerySet[Dataset]:
        if self.value() == "published":
            return queryset.filter(
                status__in=[Dataset.Status.PUBLISHED]
            )
        if self.value() == "non_published":
            return queryset.exclude(
                status__in=[Dataset.Status.PUBLISHED]
            )
        return queryset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """Admin View for Dataset"""

    list_display = ("dataset_id", "title_short_de", "data_source", "status")
    list_filter = ("data_source", PublishedNonPublished)
    readonly_fields = ("created_at", "updated_at", "dataset_list")
    search_fields = ("dataset_id", "title_short_de")
    filter_horizontal = ("concepts",)
    inlines = (
        DatasetToDatasetInline,
        DatasetToUnitInline,
        DatasetToContactInline,
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
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Dataset id cannot be updated
            # TODO: depending on how we handle identifiers, we might want implement auto-generation
            # for identifiers (probably preferrable than making it readonly in edit)
            return ("dataset_id", *self.readonly_fields)
        return self.readonly_fields
