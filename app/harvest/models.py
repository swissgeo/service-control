from functools import lru_cache
from typing import TypeVar

from django.db import models
from django.utils.translation import pgettext_lazy as _

from organization.models import Unit

T = TypeVar("T")


class PrefixLookupTable[T]:
    def __init__(self, mappings: dict[str, T]) -> None:
        self.table = dict(sorted(mappings.items(), key=lambda x: len(x[0]), reverse=True))

    def match(self, value: str) -> T | None:
        for prefix, obj in self.table.items():
            if value.startswith(prefix):
                return obj
        return None


class DatasetToUnitMapping(models.Model):
    """Mapping used to map datasets to organization units during import of harvested datasets."""

    _context = "DatasetToUnitMapping Model"

    dataset_id_prefix = models.CharField(_(_context, "Dataset ID Prefix"), max_length=100)
    organization_id = models.CharField(_(_context, "Organization ID"), max_length=100)
    unit_id = models.CharField(_(_context, "Unit ID"), default=Unit.DEFAULT_UNIT_ID, max_length=100)

    def __str__(self) -> str:
        return f"{self.dataset_id_prefix} -> {self.organization_id}: {self.unit_id}"

    @classmethod
    @lru_cache(maxsize=1)
    def table(cls) -> PrefixLookupTable[Unit]:
        """Constructs a lookup table of prefixes and units, sorted by most specific (i.e. longest)
        prefixes first.

        """
        return PrefixLookupTable(
            {
                mapping.dataset_id_prefix: unit
                for mapping in DatasetToUnitMapping.objects.all()
                if (
                    unit := Unit.objects.filter(
                        unit_id=mapping.unit_id,
                        organization__organization_id=mapping.organization_id,
                    ).first()
                )
            }
        )
