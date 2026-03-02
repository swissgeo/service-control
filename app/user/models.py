import logging

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import pgettext_lazy as _

from cognito.utils.client import Client
from user.extra_audience import remove_extra_audience

logger = logging.getLogger(__name__)


class CustomUser(models.Model):
    """CustomUser extends the Django default User model.
    A user can either be a human or a machine. Human users are stored as users in cognito, machine
    users are client apps in cognito.

    For basic human user attributes (email, first_name, last_name), cognito is the source of truth.
    Service-control is the source of truth for organizations, roles and their relations to users.
    The username holds the cognito user ID in case of human users, in the case of machine users it
    holds the app client id. The name of a machine user is stored in the last_name field of the
    default User model.
    """

    _context = "User model"

    class UserType(models.TextChoices):
        _context = "User model"
        HUMAN = "HUMAN", _(_context, "Human")
        MACHINE = "MACHINE", _(_context, "Machine")

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # User can exist without an organization -> nullable
    organization = models.ForeignKey(
        "organization.Organization", null=True, on_delete=models.SET_NULL
    )

    # user_type is an enum to differentiate human users from machine users
    user_type = models.CharField(
        _(_context, "User Type"), max_length=10, choices=UserType.choices, default=UserType.HUMAN
    )
    # Only set for machine users.
    created_by_user = models.ForeignKey("user.CustomUser", null=True, on_delete=models.SET_NULL)

    def __str__(self) -> str:
        return str(self.user.username)

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        """In case of machine users, deletes the corresponding app client in cognito."""
        if self.user_type == self.UserType.MACHINE:
            client = Client()
            if not client.delete_app_client(self.user.username):
                logger.warning("cognito app client '%s' not found, not deleted", self.user.username)
            remove_extra_audience(self.user.username)

        return super().delete(using=using, keep_parents=keep_parents)
