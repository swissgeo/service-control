from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from django.http.request import HttpRequest


@admin.register(Dataservice)
class DataserviceAdmin(admin.ModelAdmin):
    """Admin View for Dataservice"""

    list_display = ("dataservice_id", "title")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")


@admin.register(WMSDataservice)
class WMSDataserviceAdmin(admin.ModelAdmin):
    """Admin View for WMSDataservice"""

    list_display = ("dataservice_id", "title", "service_type")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")

    def get_readonly_fields(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Dataservice id cannot be updated
            return (*self.readonly_fields, "dataservice_id")
        return self.readonly_fields


@admin.register(WMTSDataservice)
class WMTSDataserviceAdmin(admin.ModelAdmin):
    """Admin View for WMTSDataservice"""

    list_display = ("dataservice_id", "title", "service_type")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")

    def get_readonly_fields(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Dataservice id cannot be updated
            return (*self.readonly_fields, "dataservice_id")
        return self.readonly_fields


@admin.register(WFSDataservice)
class WFSDataserviceAdmin(admin.ModelAdmin):
    """Admin View for WFSDataservice"""

    list_display = ("dataservice_id", "title", "service_type")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")

    def get_readonly_fields(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Dataservice id cannot be updated
            return (*self.readonly_fields, "dataservice_id")
        return self.readonly_fields


@admin.register(OGCAPIFeaturesDataservice)
class OGCAPIFeaturesDataserviceAdmin(admin.ModelAdmin):
    """Admin View for OGCAPIFeaturesDataservice"""

    list_display = ("dataservice_id", "title", "service_type")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")

    def get_readonly_fields(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Dataservice id cannot be updated
            return (*self.readonly_fields, "dataservice_id")
        return self.readonly_fields


@admin.register(OGCAPIStacDataservice)
class OGCAPIStacDataserviceAdmin(admin.ModelAdmin):
    """Admin View for OGCAPIStacDataservice"""

    list_display = ("dataservice_id", "title", "service_type")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")

    def get_readonly_fields(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Dataservice id cannot be updated
            return (*self.readonly_fields, "dataservice_id")
        return self.readonly_fields


@admin.register(GeoadminFeaturesDataservice)
class GeoadminFeaturesDataserviceAdmin(admin.ModelAdmin):
    """Admin View for GeoadminFeaturesDataservice"""

    list_display = ("dataservice_id", "title", "service_type")
    readonly_fields = ("created_at", "updated_at", "dataservice_id")

    def get_readonly_fields(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Dataservice id cannot be updated
            return (*self.readonly_fields, "dataservice_id")
        return self.readonly_fields
