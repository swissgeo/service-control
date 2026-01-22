from collections.abc import Iterable
from typing import Any

from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import pgettext_lazy as _
from ninja.errors import ValidationError


class MachineUser(models.Model):
    _context = "Machine User model"

    # Use cognito app client id as machine_user_id
    machine_user_id = models.CharField(_(_context, "Client ID"), unique=True, db_index=True)
    created = models.DateTimeField(_(_context, "Created"), auto_now_add=True)
    updated = models.DateTimeField(_(_context, "Updated"), auto_now=True)

    organization = models.ForeignKey("organization.Organization", on_delete=models.CASCADE)
    name = models.CharField(_(_context, "Name"))
    created_by_user = models.CharField(_(_context, "Create By User"))

    class Meta:
        unique_together = ("organization", "name")

    def __str__(self) -> str:
        return str(self.name)

    def save(
        self,
        *_: Any,  # args
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        """Validates the model before writing it to the database and create in cognito."""

        self.full_clean()

        try:
            # If user with same name already exists for this org, return error
            MachineUser.objects.get(organization=self.organization, name=self.name)
            raise ValidationError(errors=[{"name": "machine user with this name already exists"}])
        except MachineUser.DoesNotExist:
            super().save(
                force_insert=force_insert,
                force_update=force_update,
                using=using,
                update_fields=update_fields,
            )
