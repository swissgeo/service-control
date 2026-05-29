import logging
from collections.abc import Iterable
from typing import Any, ClassVar

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import pgettext_lazy as _
from ninja.errors import ValidationError

from cognito.utils.client import Client, OrganizationGroup, UnitGroup
from config.authorization import VPRole
from user.models import MachineUser
from utils.fields import CustomSlugField
from verified_permissions.utils.client import Client as VPClient

logger = logging.getLogger(__name__)


class OrganizationManager(models.Manager):
    def remove_data_source_id(self, data_source_id: str) -> int:
        """Remove the given data source ID from all organizations"""

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


class Organization(models.Model):
    _context = "Organization model"

    """
    Note: The "blank=False" for a model field doesn't prevent DB changes.
          It only has an effect on form validation.
    """
    organization_id = CustomSlugField(
        _(_context, "External ID"),
        max_length=100,
        unique=True,
        db_index=True,
    )

    DATA_SOURCE_CHOICE_USER_INPUT: ClassVar[str] = "user-input"
    DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION: ClassVar[str] = "bod-contact-organization"
    DATA_SOURCE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION, "BOD (contactorganization)"),
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

    created = models.DateTimeField(_(_context, "Created"), auto_now_add=True)
    updated = models.DateTimeField(_(_context, "Updated"), auto_now=True)

    name_de = models.CharField(_(_context, "Name (German)"))
    name_fr = models.CharField(_(_context, "Name (French)"))
    name_en = models.CharField(_(_context, "Name (English)"))
    name_it = models.CharField(_(_context, "Name (Italian)"), null=True, blank=True)
    name_rm = models.CharField(_(_context, "Name (Romansh)"), null=True, blank=True)

    acronym_de = models.CharField(_(_context, "Acronym (German)"))
    acronym_fr = models.CharField(_(_context, "Acronym (French)"))
    acronym_en = models.CharField(_(_context, "Acronym (English)"))
    acronym_it = models.CharField(_(_context, "Acronym (Italian)"), null=True, blank=True)
    acronym_rm = models.CharField(_(_context, "Acronym (Romansh)"), null=True, blank=True)

    vp_org_admin_policy_id = models.CharField(
        _(_context, f"Verified Permissions Policy ID for {VPRole.ORG_ADMIN.value}"),
        max_length=100,
        null=True,
        blank=True,
    )

    objects = OrganizationManager()

    def __str__(self) -> str:
        return str(self.organization_id)

    def save(
        self,
        *args: Any,  # noqa: ARG002 unused arguments
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        """Validates the model before writing it to the database and create in cognito."""

        self.full_clean()
        is_new = self._state.adding
        cognito_client = Client()
        vp_client = VPClient()
        if is_new:
            user_group = OrganizationGroup(self.organization_id)
            if not cognito_client.create_group(user_group):
                logger.warning(
                    "cognito user group '%s' already exists, not created",
                    self.organization_id,
                )
            policy_id = vp_client.create_org_admin_policy(user_group)
            self.vp_org_admin_policy_id = policy_id
        else:
            existing_org_id = Organization.objects.get(pk=self.pk).organization_id
            if self.organization_id != existing_org_id:
                raise ValidationError(errors=[{"organization_id": "cannot be updated"}])
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
        if is_new:
            # Create initial unit for the organization
            Unit.objects.create(
                organization=self,
                unit_id=Unit.DEFAULT_UNIT_ID,
                name_de="Default",
                name_fr="Default",
                name_en="Default",
                name_it="Default",
                name_rm="Default",
            )

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        """Deletes from the database and cognito. Also calls delete of the related models which
        also perform some cleanup in cognito."""

        for machine_user in MachineUser.objects.filter(organization=self):
            machine_user.delete()

        for unit in self.unit_set.all():  # ty: ignore[unresolved-attribute]
            unit.delete()

        result = super().delete(using=using, keep_parents=keep_parents)

        client = Client()
        if not client.delete_group(self.organization_id):
            logger.warning("cognito user group '%s' not found, not deleted", self.organization_id)

        vp_client = VPClient()
        vp_client.delete_policy(self.vp_org_admin_policy_id)

        return result

    def add_data_source_id(self, value: str) -> None:
        values = set(self.data_source_ids)
        values.add(value)
        self.data_source_ids = sorted(values)


class Unit(models.Model):
    _context = "Organization Unit model"

    DEFAULT_UNIT_ID = "default"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    unit_id = CustomSlugField(
        _(_context, "External ID"),
        max_length=100,
        db_index=True,
    )
    created = models.DateTimeField(_(_context, "Created"), auto_now_add=True)
    updated = models.DateTimeField(_(_context, "Updated"), auto_now=True)

    name_de = models.CharField(_(_context, "Name (German)"))
    name_fr = models.CharField(_(_context, "Name (French)"))
    name_en = models.CharField(_(_context, "Name (English)"))
    name_it = models.CharField(_(_context, "Name (Italian)"), null=True, blank=True)
    name_rm = models.CharField(_(_context, "Name (Romansh)"), null=True, blank=True)

    vp_dataset_admin_policy_id = models.CharField(
        _(_context, f"Verified Permissions Policy ID for {VPRole.DATASET_ADMIN.value}"),
        max_length=100,
        null=True,
        blank=True,
    )
    vp_dataset_contributor_policy_id = models.CharField(
        _(_context, f"Verified Permissions Policy ID for {VPRole.DATASET_CONTRIBUTOR.value}"),
        max_length=100,
        null=True,
        blank=True,
    )

    class Meta:
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["organization", "unit_id"],
                name="unique_unit_id_per_org",
                violation_error_code="unique",
                violation_error_message="Unit with this External ID already exists.",
            ),
        ]

    def __str__(self) -> str:
        if self.unit_id == self.DEFAULT_UNIT_ID:
            return f"{self.organization} (default)"
        return str(self.unit_id)

    def save(
        self,
        *args: Any,  # noqa: ARG002 unused arguments
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        """Validates the model before writing it to the database and create in cognito."""
        self.full_clean()
        client = Client()
        vp_client = VPClient()
        if self._state.adding:
            user_group = UnitGroup(self.unit_id, self.organization.organization_id)
            if not client.create_group(user_group):
                logger.warning(
                    "cognito user group '%s' already exists, not created",
                    self.unit_id,
                )
            self.vp_dataset_admin_policy_id = vp_client.create_dataset_admin_policy(user_group)
            self.vp_dataset_contributor_policy_id = vp_client.create_dataset_contributor_policy(
                user_group
            )
        else:
            existing_unit_id = Unit.objects.get(pk=self.pk).unit_id
            if self.unit_id != existing_unit_id:
                raise ValidationError(errors=[{"unit_id": "cannot be updated"}])
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        """Deletes from the database and cognito."""
        client = Client()
        result = super().delete(using=using, keep_parents=keep_parents)
        if not client.delete_group(self.unit_id):
            logger.warning("cognito user group '%s' not found, not deleted", self.unit_id)

        vp_client = VPClient()
        vp_client.delete_policy(self.vp_dataset_admin_policy_id)
        vp_client.delete_policy(self.vp_dataset_contributor_policy_id)

        return result


class Contact(models.Model):
    """Contact point of an organization.

    See eCH-0271 CI_Contact.
    """

    _context = "Organization Contact model"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
    )

    created = models.DateTimeField(_(_context, "Created"), auto_now_add=True)
    updated = models.DateTimeField(_(_context, "Updated"), auto_now=True)

    name_de = models.CharField(_(_context, "Name (German)"), null=True, blank=True)
    name_fr = models.CharField(_(_context, "Name (French)"), null=True, blank=True)
    name_en = models.CharField(_(_context, "Name (English)"), null=True, blank=True)
    name_it = models.CharField(_(_context, "Name (Italian)"), null=True, blank=True)
    name_rm = models.CharField(_(_context, "Name (Romansh)"), null=True, blank=True)

    email = models.EmailField(_(_context, "Email"), null=True, blank=True)
    phone = models.CharField(_(_context, "Phone"), null=True, blank=True)

    address_administrative_area = models.CharField(
        _(_context, "Address: Administrative Area"), null=True, blank=True
    )
    address_delivery_point = models.CharField(
        _(_context, "Address: Delivery Point"), null=True, blank=True
    )
    address_postal_code = models.CharField(
        _(_context, "Address: Postal Code"), null=True, blank=True
    )
    address_city = models.CharField(_(_context, "Address: City"), null=True, blank=True)
    address_country = models.CharField(
        _(_context, "Address: Country"), max_length=2, null=True, blank=True
    )

    url_de = models.URLField(
        _(_context, "URL (German)"),
        max_length=500,
        blank=True,
        null=True,
    )
    url_fr = models.URLField(
        _(_context, "URL (German)"),
        max_length=500,
        blank=True,
        null=True,
    )
    url_en = models.URLField(
        _(_context, "URL (German)"),
        max_length=500,
        blank=True,
        null=True,
    )
    url_it = models.URLField(
        _(_context, "URL (German)"),
        max_length=500,
        blank=True,
        null=True,
    )
    url_rm = models.URLField(
        _(_context, "URL (German)"),
        max_length=500,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("organization__organization_id", "name_en")

    def __str__(self) -> str:
        return f"{self.organization} ({self.name_en or self.name_de or self.name_fr})"
