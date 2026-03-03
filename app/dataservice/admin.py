from typing import TYPE_CHECKING, Any

from django.contrib import admin

from .models import Dataservice

if TYPE_CHECKING:
    from django.http.request import HttpRequest


@admin.register(Dataservice)
class DataserviceAdmin(admin.ModelAdmin):
    """Admin View for Dataservice"""

    list_display = ("dataservice_id", "title", "type")
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
