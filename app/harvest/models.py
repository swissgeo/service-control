from functools import lru_cache
from typing import TypeVar

from django.db import models
from django.utils.translation import pgettext_lazy as _

from dataset.models import DatasetToContact
from organization.models import Contact, Unit

T = TypeVar("T")


class PrefixLookupTable[T]:
    def __init__(self, mapping: dict[str, T]) -> None:
        self.table = dict(sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True))

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


class DatasetToContactMapping(models.Model):
    """Mapping used to map datasets by role to contacts during import of harvested contacts."""

    _context = "DatasetToContactMapping Model"

    dataset_id_prefix = models.CharField(_(_context, "Dataset ID Prefix"), max_length=100)
    role = models.CharField(
        max_length=100,
        choices=DatasetToContact.RECOMMENDED_ROLES + DatasetToContact.NOT_RECOMMENDED_ROLES,
    )
    organization_id = models.CharField(_(_context, "Organization ID"), max_length=100)
    contact_name_en = models.CharField(_(_context, "Contact Name (EN)"), null=True, blank=True)

    def __str__(self) -> str:
        return (
            f"{self.dataset_id_prefix}: {self.role} -> "
            f"{self.organization_id}: {self.contact_name_en}"
        )

    @classmethod
    @lru_cache(maxsize=1)
    def table(cls) -> dict[str, PrefixLookupTable[Contact]]:
        """Constructs a lookup table of prefixes and contacts, sorted by most specific
        (i.e. longest) prefixes first.

        """
        mappings = {}
        for mapping in DatasetToContactMapping.objects.all():
            if contact := Contact.objects.filter(
                name_en=mapping.contact_name_en,
                organization__organization_id=mapping.organization_id,
            ).first():
                mappings.setdefault(mapping.role, {})
                mappings[mapping.role][mapping.dataset_id_prefix] = contact

        return {role: PrefixLookupTable(mapping) for role, mapping in mappings.items()}
