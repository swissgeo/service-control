from typing import Any

from django.contrib import admin, messages
from django.http.request import HttpRequest

HARVEST_WARNING = (
    "This object is imported from an external source. "
    "Any changes to harvested fields might be overwritten by the next import."
)


class HarvestWarningMixin(admin.ModelAdmin):
    """Show a warning banner when editing an object that was imported by a harvester.

    Expects the model to have a ``data_source`` field and a nested
    ``DataSource`` enum with a ``USER_INPUT`` member.
    """

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> Any:
        obj = self.get_object(request, object_id)
        if obj and obj.data_source != obj.DataSource.USER_INPUT:
            messages.warning(request, HARVEST_WARNING)
        return super().change_view(request, object_id, form_url, extra_context)


class HideFieldsetsOnAddMixin(admin.ModelAdmin):
    """Hides fieldsets that only make sense for existing objects (e.g. timestamps, reverse
    relations) from the add form."""

    hidden_fieldsets_on_add: tuple[str, ...] = ("Metadata",)

    def get_fieldsets(self, request: HttpRequest, obj: Any | None = None) -> Any:
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            return [fs for fs in fieldsets if fs[0] not in self.hidden_fieldsets_on_add]
        return fieldsets
