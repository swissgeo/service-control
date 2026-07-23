from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from legal.models import GeopoliticalEntity


class FederalCantonalFilter(admin.SimpleListFilter):
    title = "Federal / Cantonal type"
    parameter_name = "custom_type"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:  # noqa: ARG002
        return [("federal_cantonal", "Federal and Cantonal")]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[GeopoliticalEntity]
    ) -> QuerySet[GeopoliticalEntity]:
        if self.value() == "federal_cantonal":
            return queryset.filter(
                type__in=[GeopoliticalEntity.Level.FEDERAL, GeopoliticalEntity.Level.CANTONAL]
            )
        return queryset


@admin.register(GeopoliticalEntity)
class GeopoliticalEntityAdmin(admin.ModelAdmin):
    """Admin View for Geopolicitcal Entity"""

    list_display = ("geopolitical_entity_id", "type", "name_de")

    list_filter = (
        "type",
        FederalCantonalFilter,
    )
