from typing import Any

from polymorphic.admin import (
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
    PolymorphicParentModelAdmin,
)

from django.contrib import admin
from django.http.request import HttpRequest

from .models import (
    Distribution,
    ExternalGeoadminFeaturesDistribution,
    ExternalGeoJSONDistribution,
    ExternalStacDistribution,
    ExternalWMSDistribution,
    ExternalWMTSDistribution,
)


@admin.register(Distribution)
class DistributionAdmin(PolymorphicParentModelAdmin):
    """Admin View for Distribution"""

    base_model = Distribution  # Optional, explicitly set here.
    child_models = [  # noqa: RUF012
        ExternalWMSDistribution,
        ExternalWMTSDistribution,
        ExternalStacDistribution,
        ExternalGeoJSONDistribution,
        ExternalGeoadminFeaturesDistribution,
    ]

    list_filter = (
        PolymorphicChildModelFilter,
        "data_source",
        ("dataset", admin.RelatedOnlyFieldListFilter),
    )
    list_display = ("distribution_id", "proto", "title_de", "dataset", "data_source")
    readonly_fields = ("sgid", "created_at", "updated_at")

    search_fields = (
        "sgid",
        "distribution_id",
        "dataset__dataset_id",
        "dataset__title_de",
        "dataset__title_short_de",
    )

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            return ("sgid", *self.readonly_fields)
        return self.readonly_fields

    @admin.display(empty_value="???")
    def proto(self, obj: Distribution) -> str:
        return obj.get_real_instance().protocol


@admin.register(ExternalWMTSDistribution)
class ExternalWMTSDistributionAdmin(PolymorphicChildModelAdmin):
    """Admin View for ExternalWMTSDistribution"""

    readonly_fields = ("sgid", "created_at", "updated_at")

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            return ("sgid", *self.readonly_fields)
        return self.readonly_fields


@admin.register(ExternalWMSDistribution)
class ExternalWMSDistributionAdmin(PolymorphicChildModelAdmin):
    """Admin View for ExternalWMSDistribution"""

    readonly_fields = ("sgid", "created_at", "updated_at")

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            return ("sgid", *self.readonly_fields)
        return self.readonly_fields


@admin.register(ExternalStacDistribution)
class ExternalStacDistributionAdmin(PolymorphicChildModelAdmin):
    """Admin View for ExternalStacDistribution"""

    readonly_fields = ("sgid", "created_at", "updated_at")
    search_fields = (
        "distribution_id",
        "dataset__dataset_id",
        "dataset__title_de",
        "dataset__title_short_de",
    )
    list_filter = (
        # DatasetFilter,
        "data_source",
        ("dataset", admin.RelatedOnlyFieldListFilter),
    )

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            return ("sgid", *self.readonly_fields)
        return self.readonly_fields


@admin.register(ExternalGeoJSONDistribution)
class ExternalGeoJSONDistributionAdmin(PolymorphicChildModelAdmin):
    """Admin View for ExternalGeoJSONDistribution"""

    readonly_fields = ("sgid", "created_at", "updated_at")
    search_fields = (
        "distribution_id",
        "dataset__dataset_id",
        "dataset__title_de",
        "dataset__title_short_de",
    )
    list_filter = (
        # DatasetFilter,
        "data_source",
        ("dataset", admin.RelatedOnlyFieldListFilter),
    )

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            return ("sgid", *self.readonly_fields)
        return self.readonly_fields


@admin.register(ExternalGeoadminFeaturesDistribution)
class ExternalGeoadminFeaturesDistributionAdmin(PolymorphicChildModelAdmin):
    """Admin View for ExternalGeoadminFeaturesDistribution"""

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            return ("sgid", *self.readonly_fields)
        return self.readonly_fields
