import logging

from asgiref.sync import sync_to_async

from django.db import models
from django.utils.translation import pgettext_lazy as _
from ninja.errors import ValidationError

from cognito.utils.client import Client
from utils.fields import CustomSlugField

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

    def __str__(self) -> str:
        return str(self.organization_id)

    async def save_and_sync(self) -> None:
        """Validates the model before writing it to the database and create in cognito."""

        await sync_to_async(self.full_clean, thread_sensitive=True)()

        if self._state.adding:
            client = Client()
            if not await client.create_group(self.organization_id):
                logger.warning(
                    "cognito user group '%s' already exists, not created",
                    self.organization_id,
                )
        else:
            existing_org_id = (await Organization.objects.aget(pk=self.pk)).organization_id
            if self.organization_id != existing_org_id:
                raise ValidationError(errors=[{"organization_id": "cannot be updated"}])

        await super().asave()

    async def delete_and_sync(self) -> tuple[int, dict[str, int]]:
        """Deletes from the database and cognito.

        Also calls delete_and_sync of related units and machine users.
        """

        async for machine_user in self.machineuser_set.all():  # type:ignore[unresolved-attribute]
            await machine_user.delete_and_sync()
        async for unit in self.unit_set.all():  # type:ignore[unresolved-attribute]
            await unit.delete_and_sync()

        result = await super().adelete()

        client = Client()
        if not await client.delete_group(self.organization_id):
            logger.warning("cognito user group '%s' not found, not deleted", self.organization_id)

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

    async def save_and_sync(self) -> None:
        """Validates the model before writing it to the database and create in cognito."""

        await sync_to_async(self.full_clean, thread_sensitive=True)()

        if self._state.adding:
            client = Client()
            if not await client.create_group(self.unit_id):
                logger.warning(
                    "cognito user group '%s' already exists, not created",
                    self.unit_id,
                )
        else:
            existing_unit_id = (await Unit.objects.aget(pk=self.pk)).unit_id
            if self.unit_id != existing_unit_id:
                raise ValidationError(errors=[{"unit_id": "cannot be updated"}])

        await super().asave()

    async def delete_and_sync(self) -> tuple[int, dict[str, int]]:
        """Deletes from the database and cognito."""

        result = await super().adelete()

        client = Client()
        if not await client.delete_group(self.unit_id):
            logger.warning("cognito user group '%s' not found, not deleted", self.unit_id)
        return result
