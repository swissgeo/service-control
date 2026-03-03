from typing import TYPE_CHECKING, Any

from django.contrib import admin

from .models import Dataset

if TYPE_CHECKING:
    from django.http.request import HttpRequest


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """Admin View for Dataset"""

    list_display = ("dataset_id", "title_short_de")
    readonly_fields = ("created_at", "updated_at")

    def get_readonly_fields(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Organization id cannot be updated
            return (*self.readonly_fields, "dataset_id")
        return self.readonly_fields
