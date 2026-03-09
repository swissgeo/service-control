import logging
from typing import TYPE_CHECKING, Any, NamedTuple

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import pgettext_lazy as _

from cognito.utils.client import Client
from config import roles
from user.extra_audience import remove_extra_audience
from verified_permissions.utils.client import Client as VPClient

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.db.models.base import ModelBase

logger = logging.getLogger(__name__)


class RoleType(models.TextChoices):
    """Enumeration of roles for user choices."""

    ORG_ADMIN = roles.ORG_ADMIN, _("Role", "Organization Admin")
    DATASET_ADMIN = roles.DATASET_ADMIN, _("Role", "Dataset Admin")
    DATASET_CONTRIBUTOR = roles.DATASET_CONTRIBUTOR, _("Role", "Dataset Contributor")


class Role(NamedTuple):
    role_id: str
    name: str
    description: str
    policy_template_id: str | None = None

    @classmethod
    def all(cls) -> list[Role]:
        policy_template_ids = settings.ROLE_POLICY_TEMPLATE_IDS
        return [
            cls(
                role_id=RoleType.ORG_ADMIN,
                name="Organization Admin",
                description="Organization administrator with full access to all resources.",
                policy_template_id=policy_template_ids.get(RoleType.ORG_ADMIN),
            ),
            cls(
                role_id=RoleType.DATASET_ADMIN,
                name="Dataset Admin",
                description="Dataset administrator with full access to all datasets of their Unit.",
                policy_template_id=policy_template_ids.get(RoleType.DATASET_ADMIN),
            ),
            cls(
                role_id=RoleType.DATASET_CONTRIBUTOR,
                name="Dataset Contributor",
                description="Dataset contributor with limited access to datasets of their Unit.",
                policy_template_id=policy_template_ids.get(RoleType.DATASET_CONTRIBUTOR),
            ),
        ]


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
        HUMAN = "HUMAN", _("User model", "Human")
        MACHINE = "MACHINE", _("User model", "Machine")

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # User can exist without an organization -> nullable
    organization = models.ForeignKey(
        "organization.Organization", null=True, on_delete=models.SET_NULL
    )
    roles = ArrayField(
        base_field=models.CharField(max_length=32, choices=RoleType.choices),
        default=list,
        blank=True,
    )

    # user_type is an enum to differentiate human users from machine users
    user_type = models.CharField(
        _(_context, "User Type"), max_length=10, choices=UserType.choices, default=UserType.HUMAN
    )
    # Only set for machine users.
    created_by_user = models.ForeignKey(
        "user.CustomUser", null=True, blank=True, on_delete=models.SET_NULL
    )
    vp_machine_user_policy_id = models.CharField(
        _(_context, "Verified Permissions Policy ID"),
        max_length=100,
        null=True,
        blank=True,
    )

    def __str__(self) -> str:
        return str(self.user.username)

    def save(
        self,
        *args: Any,  # noqa: ARG002 unused arguments
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:

        if self.user_type == self.UserType.HUMAN:
            client = Client()
            client.update_user_roles(
                self.user.username,
                self.roles,
            )

        if self.user_type == self.UserType.MACHINE and self._state.adding:
            client = VPClient()
            self.vp_machine_user_policy_id = client.create_machine_user_policy(
                client_id=self.user.username, organization_id=self.organization.organization_id
            )

        return super().save(
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
        """In case of machine users, deletes the corresponding app client in cognito."""
        if self.user_type == self.UserType.MACHINE:
            client = Client()
            if not client.delete_app_client(self.user.username):
                logger.warning("cognito app client '%s' not found, not deleted", self.user.username)
            remove_extra_audience(self.user.username)
            vp_client = VPClient()
            vp_client.delete_policy(self.vp_machine_user_policy_id)

        return super().delete(using=using, keep_parents=keep_parents)
