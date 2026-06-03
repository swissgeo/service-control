import logging
from typing import ClassVar

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import QuerySet
from django.utils.translation import pgettext_lazy as _

from utils.fields import CustomSlugField

logger = logging.getLogger(__name__)


class DatasetManager(models.Manager):
    def remove_data_source_id(self, data_source_id: str) -> int:
        """Remove the given data source ID from all datasets"""

        return self.filter(data_source_ids__contains=[data_source_id]).update(
            data_source_ids=models.Func(
                models.F("data_source_ids"),
                models.Value(data_source_id),
                function="array_remove",
            )
        )

    def existing_data_source_ids(self, data_source: str) -> set[str]:
        """Return all data source ID of all organization with the given data source."""

        return set(
            self.filter(data_source=data_source)
            .annotate(ids=models.Func("data_source_ids", function="unnest"))
            .values_list("ids", flat=True)
            .distinct()
        )


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
    data_source_ids = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        verbose_name=_(_context, "Original IDs"),
        help_text=_(_context, "List of original external IDs"),
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

    objects = DatasetManager()

    class Meta:
        verbose_name = _("Dataset Model", "Dataset")
        verbose_name_plural = _("Dataset Model", "Datasets")

    def __str__(self) -> str:
        return self.dataset_id

    def add_data_source_id(self, value: str) -> None:
        values = set(self.data_source_ids)
        values.add(value)
        self.data_source_ids = sorted(values)

    def related_datasets(self, role: str, reverse: bool = False) -> QuerySet[Dataset]:
        if reverse:
            return Dataset.objects.filter(
                dataset_relations_as_object__role=role, dataset_relations_as_object__subject=self
            )
        return Dataset.objects.filter(
            dataset_relations_as_subject__role=role, dataset_relations_as_subject__object=self
        )


class DatasetToDataset(models.Model):
    """Each dataset can be associated with another dataset in different roles.

    These are unidirectional relations in the form of [subject] is [role] of [object].
    """

    ROLE_PARENT = "parent"
    ROLE_AGGREGATE = "aggregate"
    ROLE_DERIVATE = "derivate"
    ROLE_CLIPPAGE = "clippage"

    ROLES = (
        (ROLE_PARENT, "Parent"),
        (ROLE_AGGREGATE, "Aggregate"),
        (ROLE_DERIVATE, "Derivate"),
        (ROLE_CLIPPAGE, "Clippage"),
    )

    subject = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="dataset_relations_as_subject"
    )
    object = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="dataset_relations_as_object"
    )
    role = models.CharField(max_length=100, choices=ROLES)

    class Meta:
        indexes = (models.Index(fields=["subject", "object"]),)
        verbose_name = _("DatasetToDataset Model", "Dataset Relation")

    def __str__(self) -> str:
        return f"{self.subject} is a {self.role} of {self.object}"


class DatasetToUnit(models.Model):
    """Each dataset can be associated with organizational units in different roles."""

    ROLE_OWNER = "owner"
    ROLE_MAINTAINER = "maintainer"
    ROLE_CONTRIBUTOR = "contributor"

    ROLES = (
        (ROLE_OWNER, "Owner"),
        (ROLE_MAINTAINER, "Maintainer"),
        (ROLE_CONTRIBUTOR, "Contributor"),
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

    ROLE_CUSTODIAN = "custodian"
    ROLE_OWNER = "owner"
    ROLE_DISTRIBUTOR = "distributor"
    ROLE_POINT_OF_CONTACT = "pointOfContact"
    ROLE_PUBLISHER = "publisher"
    ROLE_RESOURCE_PROVIDER = "resourceProvider"
    ROLE_USER = "user"
    ROLE_ORIGINATOR = "originator"
    ROLE_PRINCIPAL_INVESTIGATOR = "principalInvestigator"
    ROLE_PROCESSOR = "processor"
    ROLE_AUTHOR = "author"
    ROLE_SPONSOR = "sponsor"
    ROLE_CO_AUTHOR = "coAuthor"
    ROLE_COLLABORATOR = "collaborator"
    ROLE_EDITOR = "editor"
    ROLE_MEDIATOR = "mediator"
    ROLE_RIGHTS_HOLDER = "rightsHolder"
    ROLE_CONTRIBUTOR = "contributor"
    ROLE_FUNDER = "funder"
    ROLE_STAKEHOLDER = "stakeholder"

    RECOMMENDED_ROLES = (
        (ROLE_CUSTODIAN, "Custodian"),
        (ROLE_OWNER, "Owner"),
        (ROLE_DISTRIBUTOR, "Distributor"),
        (ROLE_POINT_OF_CONTACT, "Point of Contact"),
        (ROLE_PUBLISHER, "Publisher"),
    )

    NOT_RECOMMENDED_ROLES = (
        (ROLE_RESOURCE_PROVIDER, "Resource Provider"),
        (ROLE_USER, "User"),
        (ROLE_ORIGINATOR, "Originator"),
        (ROLE_PRINCIPAL_INVESTIGATOR, "Principal Investigator"),
        (ROLE_PROCESSOR, "Processor"),
        (ROLE_AUTHOR, "Author"),
        (ROLE_SPONSOR, "Sponsor"),
        (ROLE_CO_AUTHOR, "Co-Author"),
        (ROLE_COLLABORATOR, "Collaborator"),
        (ROLE_EDITOR, "Editor"),
        (ROLE_MEDIATOR, "Mediator"),
        (ROLE_RIGHTS_HOLDER, "Rights Holder"),
        (ROLE_CONTRIBUTOR, "Contributor"),
        (ROLE_FUNDER, "Funder"),
        (ROLE_STAKEHOLDER, "Stakeholder"),
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
