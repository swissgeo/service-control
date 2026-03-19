import logging
from typing import TYPE_CHECKING, Any, NamedTuple

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
from django.utils.translation import pgettext_lazy as _

from cognito.utils.client import Client
from config.authorization import VPRole
from user.extra_audience import remove_extra_audience
from verified_permissions.utils.client import Client as VPClient

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.db.models.base import ModelBase

logger = logging.getLogger(__name__)


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
                role_id=VPRole.ORG_ADMIN.value,
                name="Organization Admin",
                description="Organization administrator with full access to all resources.",
                policy_template_id=policy_template_ids.get(VPRole.ORG_ADMIN),
            ),
            cls(
                role_id=VPRole.DATASET_ADMIN.value,
                name="Dataset Admin",
                description="Dataset administrator with full access to all datasets of their Unit.",
                policy_template_id=policy_template_ids.get(VPRole.DATASET_ADMIN),
            ),
            cls(
                role_id=VPRole.DATASET_CONTRIBUTOR.value,
                name="Dataset Contributor",
                description="Dataset contributor with limited access to datasets of their Unit.",
                policy_template_id=policy_template_ids.get(VPRole.DATASET_CONTRIBUTOR),
            ),
        ]


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """CustomUser replaces the Django default User model and is set as AUTH_USER_MODEL in settings.
    A user can either be a human or a machine. Human users are stored as users in cognito, machine
    users are client apps in cognito.

    For basic human user attributes (email, first_name, last_name), cognito is the source of truth.
    Service-control is the source of truth for organizations, roles and their relations to users.
    """

    __original_roles = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__original_roles = self.roles

    _context = "User model"

    class UserType(models.TextChoices):
        HUMAN = "HUMAN", _("User model", "Human")
        MACHINE = "MACHINE", _("User model", "Machine")

    # sub is the unique identifier for both human and machine users. For human users, this is the
    # cognito user ID, for machine users this is the app client ID.
    sub = models.CharField(
        _(_context, "Sub"),
        max_length=150,
        unique=True,
        help_text=_(_context, "Cognito subject. Either user id or app client id."),
    )
    # first_name of human users as is stored in cognito. Not set for machine users.
    first_name = models.CharField(_(_context, "First Name"), max_length=150, blank=True)
    # last_name of human users as is stored in cognito. App client name for machine users.
    last_name = models.CharField(_(_context, "Last Name"), max_length=150, blank=True)
    email = models.EmailField(_(_context, "Email Address"), blank=True)
    is_staff = models.BooleanField(
        _(_context, "Staff Status"),
        default=False,
        help_text=_(_context, "Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _(_context, "Active"),
        default=True,
        help_text=_(
            _context,
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts.",
        ),
    )
    date_joined = models.DateTimeField(_(_context, "Date Joined"), default=timezone.now)

    # cognito_username is only set for human users. This is the username as stored in cognito,
    # usually the external (eIAM) reference. This is required as cognito expects this username as
    # identifier in most API calls (e.g. AdminUpdateUserAttributes).
    # The cognito_username is taken from the preferred_username header set by oauth2-proxy. It is
    # only set on the first user login and never updated as this value never changes in cognito.
    cognito_username = models.CharField(
        _(_context, "Cognito Username"),
        max_length=100,
        null=True,
        blank=True,
        unique=True,
    )
    # User can exist without an organization -> nullable
    organization = models.ForeignKey(
        "organization.Organization", null=True, on_delete=models.SET_NULL
    )
    roles = ArrayField(
        base_field=models.CharField(max_length=32, choices=VPRole.choices()),
        default=list,
        blank=True,
    )

    # user_type is an enum to differentiate human users from machine users
    user_type = models.CharField(
        _(_context, "User Type"), max_length=10, choices=UserType.choices, default=UserType.HUMAN
    )
    # Only set for machine users.
    created_by_user = models.ForeignKey(
        "CustomUser", null=True, blank=True, on_delete=models.SET_NULL
    )
    vp_machine_user_policy_id = models.CharField(
        _(_context, "Verified Permissions Policy ID"),
        max_length=100,
        null=True,
        blank=True,
    )

    # password, groups and user_permissions are set in inherited PermissionsMixin and
    # AbstractBaseUser, but not used as authentication is done externally.
    password = None
    groups = None
    user_permissions = None

    USERNAME_FIELD = "sub"

    def __str__(self) -> str:
        return str(self.sub)

    def save(
        self,
        *args: Any,  # noqa: ARG002 unused arguments
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:

        if (
            self.user_type == self.UserType.HUMAN
            and not self._state.adding
            and self.cognito_username is not None
            and self.roles != self.__original_roles
        ):
            # Custom user will be created by RemoteCustomUserBackend when the user logs in for
            # first time. At this point the user will never have roles set yet, so we can skip the
            # call to cognito to update user roles. For subsequent updates of human users, we need
            # to update the roles in cognito if they have changed.
            client = Client()
            client.update_user_roles(
                self.cognito_username,
                self.roles,
            )

        if self.user_type == self.UserType.MACHINE and self._state.adding:
            client = VPClient()
            self.vp_machine_user_policy_id = client.create_machine_user_policy(
                client_id=self.sub, organization_id=self.organization.organization_id
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
            if not client.delete_app_client(self.sub):
                logger.warning("cognito app client '%s' not found, not deleted", self.sub)
            remove_extra_audience(self.sub)
            vp_client = VPClient()
            vp_client.delete_policy(self.vp_machine_user_policy_id)

        return super().delete(using=using, keep_parents=keep_parents)
