from typing import Any

from polymorphic.admin import (
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
    PolymorphicParentModelAdmin,
)

from django.contrib import admin

from utils.admin import HarvestWarningMixin, HideFieldsetsOnAddMixin

from .models import (
    Dataservice,
    GeoadminFeaturesDataservice,
    OGCAPIFeaturesDataservice,
    OGCAPIStacDataservice,
    WFSDataservice,
    WMSDataservice,
    WMTSDataservice,
)


@admin.register(Dataservice)
class DataserviceAdmin(PolymorphicParentModelAdmin):
    """Admin View for Dataservice"""

    child_models = [  # noqa: RUF012
        WMSDataservice,
        WMTSDataservice,
        WFSDataservice,
        OGCAPIFeaturesDataservice,
        OGCAPIStacDataservice,
        GeoadminFeaturesDataservice,
    ]

    list_display = ("sgid", "dataservice_id", "title")
    readonly_fields = ("sgid", "created_at", "updated_at", "dataservice_id")
    list_filter = (PolymorphicChildModelFilter, "data_source")
    search_fields = ("sgid", "dataservice_id", "title")


def dataservice_fieldsets(service_fields: tuple[Any, ...] = ()) -> tuple[Any, ...]:
    """Fieldsets shared by all concrete dataservice types.

    `service_fields` are the service type specific fields, shown in the "Service" fieldset (which
    is omitted for types without specific fields).
    """
    service = (("Service", {"fields": service_fields}),) if service_fields else ()
    return (
        (
            "Identification",
            {
                "description": "The external ID is generated from the title when creating.",
                "fields": (
                    ("sgid", "dataservice_id"),
                    "title",
                    ("data_source", "data_source_ids"),
                ),
            },
        ),
        *service,
        (
            "Documentation",
            {
                "fields": (
                    "openapi_spec_url",
                    "documentation_url_de",
                    "documentation_url_fr",
                    "documentation_url_en",
                    "documentation_url_it",
                ),
            },
        ),
        ("Metadata", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )


class DataserviceChildAdmin(
    HarvestWarningMixin, HideFieldsetsOnAddMixin, PolymorphicChildModelAdmin
):
    """Common admin view for all concrete dataservice types."""

    list_display = ("sgid", "dataservice_id", "title", "service_type")
    readonly_fields = ("sgid", "created_at", "updated_at", "dataservice_id")
    save_on_top = True
    fieldsets = dataservice_fieldsets()


@admin.register(WMSDataservice)
class WMSDataserviceAdmin(DataserviceChildAdmin):
    """Admin View for WMSDataservice"""

    fieldsets = dataservice_fieldsets(("capabilities_url", ("languages", "default_language")))


@admin.register(WMTSDataservice)
class WMTSDataserviceAdmin(DataserviceChildAdmin):
    """Admin View for WMTSDataservice"""

    fieldsets = dataservice_fieldsets(
        ("capabilities_url", ("languages", "default_language"), "variable_epsg_list")
    )


@admin.register(WFSDataservice)
class WFSDataserviceAdmin(DataserviceChildAdmin):
    """Admin View for WFSDataservice"""


@admin.register(OGCAPIFeaturesDataservice)
class OGCAPIFeaturesDataserviceAdmin(DataserviceChildAdmin):
    """Admin View for OGCAPIFeaturesDataservice"""


@admin.register(OGCAPIStacDataservice)
class OGCAPIStacDataserviceAdmin(DataserviceChildAdmin):
    """Admin View for OGCAPIStacDataservice"""

    fieldsets = dataservice_fieldsets(("landing_page_url",))


@admin.register(GeoadminFeaturesDataservice)
class GeoadminFeaturesDataserviceAdmin(DataserviceChildAdmin):
    """Admin View for GeoadminFeaturesDataservice"""

    fieldsets = dataservice_fieldsets(("landing_page_url",))
