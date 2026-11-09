from typing import Any

from polymorphic.admin import (
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
    PolymorphicParentModelAdmin,
)

from django.conf import settings
from django.contrib import admin
from django.http.request import HttpRequest
from django.utils.html import format_html

from utils.admin import HarvestWarningMixin, HideFieldsetsOnAddMixin

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
    list_display = ("sgid", "distribution_id", "proto", "title_de", "dataset", "data_source")
    readonly_fields = ("sgid", "created_at", "updated_at", "oar_preview")

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

    @admin.display(description="Link to OAR Record from last export")
    def oar_preview(self, obj: Distribution) -> str:
        host = (
            f"{settings.APP_ENV}.sgdi.tech" if settings.APP_ENV in ("dev", "int") else "swissgeo.ch"
        )
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            f"https://services.{host}/api/oar/rc1/collections/swissgeo-distributions/items/{obj.sgid}",
            f"Preview Distribution '{obj.sgid}' in OAR API",
        )

    @admin.display(empty_value="???")
    def proto(self, obj: Distribution) -> str:
        return obj.get_real_instance().protocol


def distribution_fieldsets(service_fields: tuple[Any, ...]) -> tuple[Any, ...]:
    """Fieldsets shared by all concrete distribution types.

    `service_fields` are the protocol specific fields, shown in the "Service" fieldset.
    """
    return (
        (
            "Identification",
            {
                "fields": (
                    ("sgid", "distribution_id"),
                    "dataset",
                    ("data_source", "data_source_ids"),
                ),
            },
        ),
        (
            "Export",
            {
                "fields": ("oar_preview",),
            },
        ),
        ("Service", {"fields": (*service_fields, "meta_information")}),
        (
            "Titles",
            {"fields": ("title_de", "title_fr", "title_en", "title_it", "title_rm")},
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
        ("Metadata", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )


class DistributionChildAdmin(
    HarvestWarningMixin, HideFieldsetsOnAddMixin, PolymorphicChildModelAdmin
):
    """Common admin view for all concrete distribution types."""

    readonly_fields = ("sgid", "created_at", "updated_at", "oar_preview")
    save_on_top = True

    @admin.display(description="Link to OAR Record from last export")
    def oar_preview(self, obj: Distribution) -> str:
        host = (
            f"{settings.APP_ENV}.sgdi.tech" if settings.APP_ENV in ("dev", "int") else "swissgeo.ch"
        )
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            f"https://services.{host}/api/oar/rc1/collections/swissgeo-distributions/items/{obj.sgid}",
            f"Preview Distribution '{obj.sgid}' in OAR API",
        )

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            return ("sgid", *self.readonly_fields)
        return self.readonly_fields


@admin.register(ExternalWMTSDistribution)
class ExternalWMTSDistributionAdmin(DistributionChildAdmin):
    """Admin View for ExternalWMTSDistribution"""

    fieldsets = distribution_fieldsets(
        (
            "dataservice",
            "wmts_layer_name_de",
            "wmts_layer_name_fr",
            "wmts_layer_name_en",
            "wmts_layer_name_it",
            "wmts_layer_name_rm",
            "opacity",
        )
    )


@admin.register(ExternalWMSDistribution)
class ExternalWMSDistributionAdmin(DistributionChildAdmin):
    """Admin View for ExternalWMSDistribution"""

    fieldsets = distribution_fieldsets(
        (
            "dataservice",
            "wms_layer_name_de",
            "wms_layer_name_fr",
            "wms_layer_name_en",
            "wms_layer_name_it",
            "wms_layer_name_rm",
            ("opacity", "gutter"),
        )
    )


@admin.register(ExternalStacDistribution)
class ExternalStacDistributionAdmin(DistributionChildAdmin):
    """Admin View for ExternalStacDistribution"""

    fieldsets = distribution_fieldsets(("dataservice", "stac_collection_id"))
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


@admin.register(ExternalGeoJSONDistribution)
class ExternalGeoJSONDistributionAdmin(DistributionChildAdmin):
    """Admin View for ExternalGeoJSONDistribution"""

    fieldsets = distribution_fieldsets(
        (
            "geojson_url_de",
            "geojson_url_fr",
            "geojson_url_en",
            "geojson_url_it",
            "geojson_url_rm",
            "style_url",
        )
    )
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


@admin.register(ExternalGeoadminFeaturesDistribution)
class ExternalGeoadminFeaturesDistributionAdmin(DistributionChildAdmin):
    """Admin View for ExternalGeoadminFeaturesDistribution"""

    fieldsets = distribution_fieldsets(("dataservice", "layer_id", ("queryable", "renderable")))
