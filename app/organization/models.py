import logging
from collections.abc import Iterable
from typing import Any

from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import pgettext_lazy as _
from ninja.errors import ValidationError

from cognito.utils.client import Client
from utils.fields import CustomSlugField

logger = logging.getLogger(__name__)

# TODO check if we can fix the DJ001, DJ012 warnings
# ruff: noqa: DJ001, DJ012


class Organization(models.Model):
    _context = "Organization model"

    def __str__(self) -> str:
        return str(self.organization_id)

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
            if not client.create_group(self.organization_id):
                logger.warning(
                    "cognito user group '%s' already exists, not created",
                    self.organization_id,
                )
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
        """Deletes from the database and cognito."""

        client = Client()
        result = super().delete(using=using, keep_parents=keep_parents)
        if not client.delete_group(self.organization_id):
            logger.warning("cognito user group '%s' not found, not deleted", self.organization_id)
        return result
