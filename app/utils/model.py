from typing import TYPE_CHECKING, cast

from django.db import models


class ExternalIdsManagerMixin:
    """Shared manager methods for models that have a external_ids JSON field."""

    if TYPE_CHECKING:
        from typing import Any  # noqa: PLC0415

        from polymorphic.managers import _All, _Base  # noqa: PLC0415
        from polymorphic.query import PolymorphicQuerySet  # noqa: PLC0415

        def filter(self, *args: Any, **kwargs: Any) -> PolymorphicQuerySet[_All, _Base]: ...

    def remove_external_id(self, data_source: str, external_id: str) -> None:
        """Remove the given external ID from all records."""

        value = {"source": data_source, "id": external_id}
        for obj in self.filter(external_ids__contains=[value]):
            obj.external_ids = [entry for entry in obj.external_ids if entry != value]
            obj.save(update_fields=["external_ids"])

    def existing_external_ids(self, data_source: str) -> set[str]:
        """Return all external IDs for records with the given data source."""

        datasets = self.filter(external_ids__contains=[{"source": data_source}]).values_list(
            "external_ids", flat=True
        )
        return {
            entry["id"]
            for entries in datasets
            for entry in entries
            if entry["source"] == data_source
        }


class ExternalIdsModelMixin:
    external_ids: models.JSONField

    def add_external_id(self, data_source: str, external_id: str) -> None:
        entry = {"source": data_source, "id": external_id}
        entries = cast("list[dict[str, str]]", self.external_ids)
        if entry not in entries:
            entries.append(entry)
        entries.sort(key=lambda e: (e["source"], e["id"]))
        self.external_ids = entries
