from typing import TypeVar

from django.db import models
from django.utils.translation import pgettext_lazy as _

from dataset.models import Dataset, DatasetToContact
from organization.models import Contact, Organization, Unit

T = TypeVar("T")
M = TypeVar("M")


class PrefixLookupTable[T, M]:
    def __init__(self, mapping: dict[str, tuple[T, M]]) -> None:
        self.table = dict(sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True))

    def match(self, value: str) -> tuple[T, M] | tuple[None, None]:
        for prefix, (obj, mapping) in self.table.items():
            if value.startswith(prefix):
                refresh_from_db = getattr(obj, "refresh_from_db", None)
                if callable(refresh_from_db):
                    refresh_from_db()
                return (obj, mapping)
        return None, None


class OrganizationMapping(models.Model):
    """Mapping used to map providers/organization during import of harvested organizations."""

    _context = "OrganizationMapping Model"

    provider_id_prefix = models.CharField(
        _(_context, "Prefix"),
        max_length=100,
        help_text=_(
            _context,
            (
                "Prefix used for matching provider ID during import of organizations from harvest "
                "table/BOD"
            ),
        ),
    )
    organization_id = models.CharField(
        _(_context, "Organization ID"),
        max_length=100,
        help_text=_(_context, "The ID of the organization in this database"),
    )
    update = models.BooleanField(
        _(_context, "Update"),
        default=False,
        help_text=_(_context, "Whetever the matching entry should update the organization"),
    )

    def __str__(self) -> str:
        return f"{self.provider_id_prefix} -> {self.organization_id}"

    @classmethod
    def table(cls) -> PrefixLookupTable[Organization, OrganizationMapping]:
        """Constructs a lookup table of prefixes and organizations, sorted by most specific
        (i.e. longest) prefixes first.

        """
        return PrefixLookupTable(
            {
                mapping.provider_id_prefix: (organization, mapping)
                for mapping in OrganizationMapping.objects.all()
                if (
                    organization := Organization.objects.filter(
                        organization_id=mapping.organization_id,
                    ).first()
                )
            }
        )


class DatasetMapping(models.Model):
    """Mapping used to map datasets during import of harvested datasets and STAC sync."""

    _context = "DatasetMapping Model"

    dataset_id_prefix = models.CharField(
        _(_context, "Prefix"),
        max_length=100,
        help_text=_(
            _context,
            "<br>".join(  # noqa:FLY002
                (
                    "Prefix used for matching:",
                    "- Dataset ID during import of datasets from harvest table/BOD (if enabled)",
                    "- Layer ID during import of distributions from harvest table/BOD (if enabled)",
                    "- STAC Collection ID during syncing distributions from capabilities "
                    "(if enabled)",
                )
            ),
        ),
    )
    dataset_id = models.CharField(
        _(_context, "Dataset ID"),
        max_length=100,
        help_text=_(_context, "The ID of the dataset in this database"),
    )
    enabled_for_bod_dataset = models.BooleanField(
        _(_context, "Datasets"),
        default=True,
        help_text=_(
            _context,
            (
                "Whetever the matching entry should be used while importing datasets from "
                "harvest tables/BOD"
            ),
        ),
    )
    enabled_for_bod_distribution = models.BooleanField(
        _(_context, "Distributions (BOD)"),
        default=True,
        help_text=_(
            _context,
            (
                "Whetever the matching entry should be used while importing distributions from "
                "harvest tables/BOD"
            ),
        ),
    )
    enabled_for_stac_distribution = models.BooleanField(
        _(_context, "Distributions (STAC)"),
        default=True,
        help_text=_(
            _context,
            "Whetever the matching entry should be used while importing distributions from STAC",
        ),
    )
    update = models.BooleanField(
        _(_context, "Update"),
        default=False,
        help_text=_(
            _context, "Whetever the matching entry should update the dataset or distribution"
        ),
    )

    def __str__(self) -> str:
        return f"{self.dataset_id_prefix} -> {self.dataset_id}"

    @classmethod
    def table(cls) -> PrefixLookupTable[Dataset, DatasetMapping]:
        """Constructs a lookup table of prefixes and datasets, sorted by most specific
        (i.e. longest) prefixes first.

        """
        return PrefixLookupTable(
            {
                mapping.dataset_id_prefix: (dataset, mapping)
                for mapping in DatasetMapping.objects.all()
                if (
                    dataset := Dataset.objects.filter(
                        dataset_id=mapping.dataset_id,
                    ).first()
                )
            }
        )


class DatasetToUnitMapping(models.Model):
    """Mapping used to map datasets to organization units during import of harvested datasets."""

    _context = "DatasetToUnitMapping Model"

    dataset_id_prefix = models.CharField(
        _(_context, "Prefix"),
        max_length=100,
        help_text=_(
            _context,
            "Prefix used for matching dataset ID during import of datasets from harvest/BOD",
        ),
    )
    organization_id = models.CharField(
        _(_context, "Organization ID"),
        max_length=100,
        help_text=_(_context, "The ID of the organization in this database"),
    )
    unit_id = models.CharField(
        _(_context, "Unit ID"),
        default=Unit.DEFAULT_UNIT_ID,
        max_length=100,
        help_text=_(_context, "The ID of the organization unit in this database"),
    )

    def __str__(self) -> str:
        return f"{self.dataset_id_prefix} -> {self.organization_id}: {self.unit_id}"

    @classmethod
    def table(cls) -> PrefixLookupTable[Unit, DatasetToUnitMapping]:
        """Constructs a lookup table of prefixes and units, sorted by most specific (i.e. longest)
        prefixes first.

        """
        return PrefixLookupTable(
            {
                mapping.dataset_id_prefix: (unit, mapping)
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

    dataset_id_prefix = models.CharField(
        _(_context, "Dataset ID Prefix"),
        max_length=100,
        help_text=_(
            _context,
            "Prefix used for matching dataset ID during import of datasets from harvest/geocat",
        ),
    )
    role = models.CharField(
        max_length=100,
        choices=DatasetToContact.Role.choices,
        help_text=_(
            _context,
            "Role used for matching during import of datasets from harvest/geocat",
        ),
    )
    organization_id = models.CharField(
        _(_context, "Organization ID"),
        max_length=100,
        help_text=_(_context, "The ID of the organization in this database"),
    )
    contact_name_en = models.CharField(
        _(_context, "Contact Name (EN)"),
        null=True,
        blank=True,
        help_text=_(_context, "The contact name (EN) of the organization contact in this database"),
    )

    def __str__(self) -> str:
        return (
            f"{self.dataset_id_prefix}: {self.role} -> "
            f"{self.organization_id}: {self.contact_name_en}"
        )

    @classmethod
    def table(cls) -> dict[str, PrefixLookupTable[Contact, DatasetToContactMapping]]:
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
                mappings[mapping.role][mapping.dataset_id_prefix] = (contact, mapping)

        return {role: PrefixLookupTable(mapping) for role, mapping in mappings.items()}
