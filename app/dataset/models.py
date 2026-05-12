import logging
from typing import ClassVar

from django.db import models
from django.utils.translation import pgettext_lazy as _

from utils.fields import CustomSlugField

logger = logging.getLogger(__name__)


class Dataset(models.Model):
    """Dataset model."""

    _context = "Dataset Model"

    dataset_id = CustomSlugField(_(_context, "External ID"), unique=True, max_length=100)

    DATA_SOURCE_CHOICE_USER_INPUT: ClassVar[str] = "user-input"
    DATA_SOURCE_CHOICE_BOD_DATASET: ClassVar[str] = "bod-dataset"
    DATA_SOURCE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (DATA_SOURCE_CHOICE_BOD_DATASET, "BOD (dataset)"),
        (DATA_SOURCE_CHOICE_USER_INPUT, "User Input (Admin UI/API)"),
    ]
    data_source = models.CharField(
        _(_context, "Data Source"),
        choices=DATA_SOURCE_CHOICES,
        default=DATA_SOURCE_CHOICE_USER_INPUT,
        max_length=255,
    )

    # The title we currently harvest from BOD and store here is actually a short
    # version of the original title. In a later iteration, we'll add the original
    # title as well.
    title_short_de = models.CharField(_(_context, "Title (German)"))
    title_short_fr = models.CharField(_(_context, "Title (French)"))
    title_short_en = models.CharField(_(_context, "Title (English)"))
    title_short_it = models.CharField(_(_context, "Title (Italian)"), null=True, blank=True)
    title_short_rm = models.CharField(_(_context, "Title (Romansh)"), null=True, blank=True)

    description_de = models.TextField(_(_context, "Description (German)"))
    description_fr = models.TextField(_(_context, "Description (French)"))
    description_en = models.TextField(_(_context, "Description (English)"))
    description_it = models.TextField(_(_context, "Description (Italian)"), null=True, blank=True)
    description_rm = models.TextField(_(_context, "Description (Romansh)"), null=True, blank=True)

    geocat_id = models.CharField(_(_context, "Geocat ID"), unique=True, max_length=100)

    preferred_distribution = models.ForeignKey(
        "distribution.Distribution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_for_datasets",
    )

    keywords = models.ManyToManyField("thesaurus.Keyword", related_name="keywords", blank=True)

    units = models.ManyToManyField(
        "organization.Unit", through="DatasetToUnit", related_name="datasets"
    )
    contacts = models.ManyToManyField(
        "organization.Contact", through="DatasetToContact", related_name="datasets"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_(_context, "Created at"),
        help_text=_(_context, "Date and time when the dataset was created"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_(_context, "Updated at"),
        help_text=_(_context, "Date and time when the dataset was last updated"),
    )

    # Stores the contacts as defined in geocat (until service-control becomes data master for these)
    legacy_contacts = models.JSONField(_(_context, "Contacts (Legacy)"), default=list, blank=True)

    class Meta:
        verbose_name = _("Dataset Model", "Dataset")
        verbose_name_plural = _("Dataset Model", "Datasets")

    def __str__(self) -> str:
        return self.dataset_id


class DatasetToUnit(models.Model):
    """Each dataset can be associated with organizational units in different roles."""

    ROLES = (
        ("owner", "Owner"),
        ("maintainer", "Maintainer"),
        ("contributor", "Contributor"),
    )

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="dataset_units")
    unit = models.ForeignKey(
        "organization.Unit", on_delete=models.CASCADE, related_name="dataset_units"
    )
    role = models.CharField(max_length=100, choices=ROLES)

    class Meta:
        indexes = (models.Index(fields=["dataset", "unit"]),)
        verbose_name = _("DatasetToUnit Model", "Dataset Unit")

    def __str__(self) -> str:
        return f"{self.unit} as {self.role} in {self.dataset}"


class DatasetToContact(models.Model):
    """A dataset can have different contacts with specific roles.

    See eCH-0271: CI_RoleCode.
    """

    RECOMMENDED_ROLES = (
        ("custodian", "Custodian"),
        ("owner", "Owner"),
        ("distributor", "Distributor"),
        ("pointOfContact", "Point of Contact"),
        ("publisher", "Publisher"),
    )

    NOT_RECOMMENDED_ROLES = (
        ("resourceProvider", "Resource Provider"),
        ("user", "User"),
        ("originator", "Originator"),
        ("principalInvestigator", "Principal Investigator"),
        ("processor", "Processor"),
        ("author", "Author"),
        ("sponsor", "Sponsor"),
        ("coAuthor", "Co-Author"),
        ("collaborator", "Collaborator"),
        ("editor", "Editor"),
        ("mediator", "Mediator"),
        ("rightsHolder", "Rights Holder"),
        ("contributor", "Contributor"),
        ("funder", "Funder"),
        ("stakeholder", "Stakeholder"),
    )

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="dataset_contacts")
    contact = models.ForeignKey(
        "organization.Contact", on_delete=models.CASCADE, related_name="dataset_contacts"
    )
    role = models.CharField(max_length=100, choices=RECOMMENDED_ROLES + NOT_RECOMMENDED_ROLES)

    class Meta:
        indexes = (models.Index(fields=["dataset", "contact"]),)
        verbose_name = _("DatasetToContact Model", "Dataset Contact")

    def __str__(self) -> str:
        return f"{self.contact} as {self.role} in {self.dataset}"
