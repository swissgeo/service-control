import logging
from typing import TYPE_CHECKING, Any, ClassVar

from django.db import models
from django.utils.translation import pgettext_lazy as _

from cognito.utils.client import Client
from user.extra_audience import remove_extra_audience

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.db.models.base import ModelBase

logger = logging.getLogger(__name__)


class User(models.Model):
    """Represents a user.

    Users are stored in cognito. User attributes are taken from cognito:
    +----------------------------
    | Cognito -> User model
    +----------------------------
    | User Name -> username
    +----------------------------
    """

    _context = "User model"

    username = models.CharField(_(_context, "Username"), unique=True, db_index=True)
    created = models.DateTimeField(_(_context, "Created"), auto_now_add=True)
    updated = models.DateTimeField(_(_context, "Updated"), auto_now=True)
    deleted_at = models.DateTimeField(_(_context, "deleted at"), null=True, blank=True)

    # User can exist without an organization -> nullable
    organization = models.ForeignKey(
        "organization.Organization", null=True, on_delete=models.SET_NULL
    )

    def __str__(self) -> str:
        return str(self.username)


class MachineUser(models.Model):
    _context = "Machine User model"

    # Use cognito app client id as machine_user_id
    machine_user_id = models.CharField(_(_context, "Client ID"), unique=True, db_index=True)
    created = models.DateTimeField(_(_context, "Created"), auto_now_add=True)
    updated = models.DateTimeField(_(_context, "Updated"), auto_now=True)

    organization = models.ForeignKey("organization.Organization", on_delete=models.CASCADE)
    name = models.CharField(_(_context, "Name"))
    # created_by_user is the username as provided by cognito. If/Once we introduce a user model in
    # the database we can change this to a foreign key.
    created_by_user = models.CharField(_(_context, "Create By User"))

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                name="user_machineuser_organization_name_uniq",
                fields=["organization", "name"],
                violation_error_message="machine user with this name already exists",
            )
        ]

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

        # full clean required for contrain validation to run properly
        self.full_clean()
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
        if not client.delete_app_client(self.machine_user_id):
            logger.warning("cognito app client '%s' not found, not deleted", self.machine_user_id)
        remove_extra_audience(self.machine_user_id)

        return super().delete(using=using, keep_parents=keep_parents)
