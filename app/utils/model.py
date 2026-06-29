from typing import TYPE_CHECKING

from django.contrib.postgres.fields import ArrayField
from django.db import models


class DataSourceIdManagerMixin:
    """Shared manager methods for models that have a data_source_ids array field."""

    if TYPE_CHECKING:
        from typing import Any  # noqa: PLC0415

        from polymorphic.managers import _All, _Base  # noqa: PLC0415
        from polymorphic.query import PolymorphicQuerySet  # noqa: PLC0415

        def filter(self, *args: Any, **kwargs: Any) -> PolymorphicQuerySet[_All, _Base]: ...

    def remove_data_source_id(self, data_source_id: str) -> int:
        """Remove the given data source ID from all records."""

        return self.filter(data_source_ids__contains=[data_source_id]).update(
            data_source_ids=models.Func(
                models.F("data_source_ids"),
                models.Value(data_source_id),
                function="array_remove",
            )
        )

    def existing_data_source_ids(self, data_source: str) -> set[str]:
        """Return all data source IDs for records with the given data source."""

        return set(
            self.filter(data_source=data_source)
            .annotate(ids=models.Func("data_source_ids", function="unnest"))
            .values_list("ids", flat=True)
            .distinct()
        )


class DataSourceIdModelMixin:
    data_source_ids: ArrayField

    def add_data_source_id(self, value: str) -> None:
        values = set(self.data_source_ids)  # ty:ignore[invalid-argument-type]
        values.add(value)
        self.data_source_ids = sorted(values)
