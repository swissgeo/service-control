from polymorphic.admin import (
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
    PolymorphicParentModelAdmin,
)

from django.contrib import admin

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
    child_models = (
        ExternalWMSDistribution,
        ExternalWMTSDistribution,
        ExternalStacDistribution,
        ExternalGeoJSONDistribution,
        ExternalGeoadminFeaturesDistribution,
    )

    list_filter = (
        PolymorphicChildModelFilter,
        "data_source",
        ("dataset", admin.RelatedOnlyFieldListFilter),
    )
    list_display = ("distribution_id", "title", "dataset", "data_source")
    readonly_fields = ("created_at", "updated_at")

    search_fields = (
        "distribution_id",
        "dataset__dataset_id",
        "dataset__title_short_de",
    )


@admin.register(ExternalWMTSDistribution)
class ExternalWMTSDistributionAdmin(PolymorphicChildModelAdmin):
    """Admin View for ExternalWMTSDistribution"""

    list_display = ("distribution_id", "title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ExternalWMSDistribution)
class ExternalWMSDistributionAdmin(PolymorphicChildModelAdmin):
    """Admin View for ExternalWMSDistribution"""

    list_display = ("distribution_id", "title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ExternalStacDistribution)
class ExternalStacDistributionAdmin(PolymorphicChildModelAdmin):
    """Admin View for ExternalStacDistribution"""

    list_display = ("distribution_id", "dataset", "data_source")
    readonly_fields = ("created_at", "updated_at")
    search_fields = (
        "distribution_id",
        "dataset__dataset_id",
        "dataset__title_short_de",
    )
    list_filter = (
        # DatasetFilter,
        "data_source",
        ("dataset", admin.RelatedOnlyFieldListFilter),
    )


@admin.register(ExternalGeoJSONDistribution)
class ExternalGeoJSONDistributionAdmin(PolymorphicChildModelAdmin):
    """Admin View for ExternalGeoJSONDistribution"""

    list_display = ("distribution_id", "dataset", "data_source")
    readonly_fields = ("created_at", "updated_at")
    search_fields = (
        "distribution_id",
        "dataset__dataset_id",
        "dataset__title_short_de",
    )
    list_filter = (
        # DatasetFilter,
        "data_source",
        ("dataset", admin.RelatedOnlyFieldListFilter),
    )


@admin.register(ExternalGeoadminFeaturesDistribution)
class ExternalGeoadminFeaturesDistributionAdmin(PolymorphicChildModelAdmin):
    """Admin View for ExternalGeoadminFeaturesDistribution"""
