from polymorphic.admin import (
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
    PolymorphicParentModelAdmin,
)

from django.contrib import admin

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

    base_model = Dataservice  # Optional, explicitly set here.
    child_models = (
        WMSDataservice,
        WMTSDataservice,
        WFSDataservice,
        OGCAPIFeaturesDataservice,
        OGCAPIStacDataservice,
        GeoadminFeaturesDataservice,
    )

    list_display = ("dataservice_id", "title")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")
    list_filter = (PolymorphicChildModelFilter,)  # This is optional.


@admin.register(WMSDataservice)
class WMSDataserviceAdmin(PolymorphicChildModelAdmin):
    """Admin View for WMSDataservice"""

    list_display = ("dataservice_id", "title", "service_type")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")


@admin.register(WMTSDataservice)
class WMTSDataserviceAdmin(PolymorphicChildModelAdmin):
    """Admin View for WMTSDataservice"""

    list_display = ("dataservice_id", "title", "service_type")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")


@admin.register(WFSDataservice)
class WFSDataserviceAdmin(PolymorphicChildModelAdmin):
    """Admin View for WFSDataservice"""

    list_display = ("dataservice_id", "title", "service_type")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")


@admin.register(OGCAPIFeaturesDataservice)
class OGCAPIFeaturesDataserviceAdmin(PolymorphicChildModelAdmin):
    """Admin View for OGCAPIFeaturesDataservice"""

    list_display = ("dataservice_id", "title", "service_type")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")


@admin.register(OGCAPIStacDataservice)
class OGCAPIStacDataserviceAdmin(PolymorphicChildModelAdmin):
    """Admin View for OGCAPIStacDataservice"""

    list_display = ("dataservice_id", "title", "service_type")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")


@admin.register(GeoadminFeaturesDataservice)
class GeoadminFeaturesDataserviceAdmin(PolymorphicChildModelAdmin):
    """Admin View for GeoadminFeaturesDataservice"""

    list_display = ("dataservice_id", "title", "service_type")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")
