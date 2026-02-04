import logging
from typing import ClassVar

from asgiref.sync import sync_to_async

from django.db import models
from django.utils.translation import pgettext_lazy as _
from ninja.errors import ValidationError

from cognito.utils.client import Client, CreateClientResponse
from user.extra_audience import add_extra_audience, remove_extra_audience

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

    async def save_and_sync(self, token_duration_mins: int | None = None) -> CreateClientResponse:
        """Validates the model before writing it to the database and create in cognito."""

        # Create cognito app client
        if self._state.adding:
            cognito_client = Client()
            app_client = await cognito_client.create_app_client(self.name, token_duration_mins)

            try:
                # Save app client info in database
                self.machine_user_id = app_client.client_id
                await sync_to_async(self.full_clean, thread_sensitive=True)()
                await self.asave()
            except:
                await cognito_client.delete_app_client(app_client.client_id)
                raise

            try:
                # Add client id for Oauth2-Proxy
                await add_extra_audience(app_client.client_id)
            except Exception:
                await self.adelete()
                await cognito_client.delete_app_client(app_client.client_id)
                raise

        else:
            existing_machine_user_id = (await MachineUser.objects.aget(pk=self.pk)).machine_user_id
            if self.machine_user_id != existing_machine_user_id:
                raise ValidationError(errors=[{"machine_user_id": "cannot be updated"}])

            await self.asave()

            app_client = CreateClientResponse(
                name=self.name, client_id=self.machine_user_id, client_secret=""
            )

        return app_client

    async def delete_and_sync(self) -> tuple[int, dict[str, int]]:
        """Deletes from the database and cognito."""

        cognito_client = Client()
        if not await cognito_client.delete_app_client(self.machine_user_id):
            logger.warning("cognito app client '%s' not found, not deleted", self.machine_user_id)
        await remove_extra_audience(self.machine_user_id)

        return await self.adelete()
