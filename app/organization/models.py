import logging
from typing import TYPE_CHECKING, Any

from django.db import models
from django.utils.translation import pgettext_lazy as _
from ninja.errors import ValidationError

from cognito.utils.client import Client
from config.authorization import VPRole
from user.models import MachineUser
from utils.fields import CustomSlugField
from verified_permissions.utils.client import Client as VPClient

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.db.models.base import ModelBase

logger = logging.getLogger(__name__)


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
        cognito_client = Client()
        vp_client = VPClient()
        if self._state.adding:
            if not cognito_client.create_group(self.organization_id):
                logger.warning(
                    "cognito user group '%s' already exists, not created",
                    self.organization_id,
                )
            policy_id = vp_client.create_org_admin_policy(
                self.organization_id,
            )
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

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        """Deletes from the database and cognito. Also calls delete of the related models which
        also perform some cleanup in cognito."""

        for machine_user in MachineUser.objects.filter(organization=self):
            machine_user.delete()

        for unit in self.unit_set.all():  # type:ignore[unresolved-attribute]
            unit.delete()

        result = super().delete(using=using, keep_parents=keep_parents)

        client = Client()
        if not client.delete_group(self.organization_id):
            logger.warning("cognito user group '%s' not found, not deleted", self.organization_id)

        vp_client = VPClient()
        vp_client.delete_policy(self.vp_org_admin_policy_id)

        return result


class Unit(models.Model):
    _context = "Organization Unit model"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
    )
    unit_id = CustomSlugField(
        _(_context, "External ID"),
        max_length=100,
        unique=True,
        db_index=True,
    )
    created = models.DateTimeField(_(_context, "Created"), auto_now_add=True)
    updated = models.DateTimeField(_(_context, "Updated"), auto_now=True)

    name_de = models.CharField(_(_context, "Name (German)"))
    name_fr = models.CharField(_(_context, "Name (French)"))
    name_en = models.CharField(_(_context, "Name (English)"))
    name_it = models.CharField(_(_context, "Name (Italian)"), null=True, blank=True)
    name_rm = models.CharField(_(_context, "Name (Romansh)"), null=True, blank=True)

    def __str__(self) -> str:
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
        if self._state.adding:
            if not client.create_group(self.unit_id):
                logger.warning(
                    "cognito user group '%s' already exists, not created",
                    self.unit_id,
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
        return result
