import logging
from typing import TYPE_CHECKING, Any, NamedTuple

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
from django.utils.translation import pgettext_lazy as _

from cognito.utils.client import Client, OrganizationGroup, UnitGroup
from config.authorization import VPRole
from user.extra_audience import remove_extra_audience
from utils.exceptions import ConflictError
from utils.fields import CustomSlugField
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

    _original_roles = None
    _original_unit_id = None
    _original_organization_id = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._original_roles = self.roles
        self._original_unit_id = getattr(self, "unit_id", None)
        self._original_organization_id = getattr(self, "organization_id", None)

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
    # User can exist without an organization -> nullable
    organization = models.ForeignKey(
        "organization.Organization", null=True, blank=True, on_delete=models.SET_NULL
    )
    # User can exist without a unit -> nullable
    unit = models.ForeignKey("organization.Unit", null=True, blank=True, on_delete=models.SET_NULL)
    # user_type is an enum to differentiate human users from machine users
    user_type = models.CharField(
        _(_context, "User Type"), max_length=10, choices=UserType.choices, default=UserType.HUMAN
    )

    # --
    # -- Human user specific fields --
    # --
    # first_name of human users as is stored in cognito.
    first_name = models.CharField(_(_context, "First Name"), max_length=150, blank=True)
    # last_name of human users as is stored in cognito.
    last_name = models.CharField(_(_context, "Last Name"), max_length=150, blank=True)
    email = models.EmailField(_(_context, "Email Address"), blank=True)
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
    roles = ArrayField(
        base_field=models.CharField(max_length=32, choices=VPRole.choices()),
        default=list,
        blank=True,
    )

    # --
    # -- Machine user specific fields --
    # --
    # App client name of machine user.
    name = models.CharField(_(_context, "Name"), max_length=150, blank=True)
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

    @property
    def unit_changed(self) -> bool:
        return self.organization_changed or self._original_unit_id != getattr(self, "unit_id", None)

    @property
    def organization_changed(self) -> bool:
        return self._original_organization_id != getattr(self, "organization_id", None)

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

        if self.unit and self.unit.organization != self.organization:
            raise ValueError("Unit must belong to the same organization as the user")

        result = super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

        # Update original values to reflect the state after save
        self._original_roles = self.roles
        self._original_unit_id = getattr(self, "unit_id", None)
        self._original_organization_id = getattr(self, "organization_id", None)

        return result

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        return super().delete(using=using, keep_parents=keep_parents)


class MachineUserManager(models.Manager):
    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset().filter(user_type=CustomUser.UserType.MACHINE)


class HumanUserManager(models.Manager):
    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset().filter(user_type=CustomUser.UserType.HUMAN)


class MachineUser(CustomUser):
    objects = MachineUserManager()

    class Meta:
        proxy = True
        verbose_name = "Machine User"
        verbose_name_plural = "Machine Users"
        ordering = ("name",)

    def save(
        self,
        *args: Any,  # noqa: ARG002 unused arguments
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.user_type = self.UserType.MACHINE

        if self._state.adding:
            client = VPClient()
            self.vp_machine_user_policy_id = client.create_machine_user_policy(
                client_id=self.sub, organization_id=self.organization.organization_id
            )
        elif self.organization_changed or self.unit_changed:
            raise ValueError(
                "Changing organization or unit of a machine user is not allowed. "
                "Remove it and create a new one instead."
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
        """Deletes the corresponding app client in cognito."""
        client = Client()
        if not client.delete_app_client(self.sub):
            logger.warning("cognito app client '%s' not found, not deleted", self.sub)
        remove_extra_audience(self.sub)
        vp_client = VPClient()
        vp_client.delete_policy(self.vp_machine_user_policy_id)

        return super().delete(using=using, keep_parents=keep_parents)


class HumanUser(CustomUser):
    objects = HumanUserManager()

    def save(
        self,
        *args: Any,  # noqa: ARG002 unused arguments
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.user_type = self.UserType.HUMAN

        if self.unit and self.unit.organization != self.organization:
            raise ValueError("Unit must belong to the same organization as the user")

        client = Client()

        if (
            not self._state.adding
            and self.cognito_username is not None
            and set(self.roles or []) != set(self._original_roles or [])
        ):
            # Custom user will be created by RemoteCustomUserBackend when the user logs in for
            # first time. At this point the user will never have roles set yet, so we can skip
            # the call to cognito to update user roles. For subsequent updates of human users,
            # we need to update the roles in cognito if they have changed.
            client.update_user_roles(
                self.cognito_username,
                self.roles,
            )

        if (
            self.unit_changed
            and self._original_unit_id is not None
            and self._original_organization_id is not None
        ):
            # Use apps to get model due to circular import
            Organization = apps.get_model("organization", "Organization")
            Unit = apps.get_model("organization", "Unit")
            original_unit = Unit.objects.filter(pk=self._original_unit_id).get()
            client.remove_user_from_group(
                self.cognito_username,
                UnitGroup(original_unit.unit_id, original_unit.organization.organization_id),
            )

        if self.organization_changed and self._original_organization_id is not None:
            # Use apps to get model due to circular import
            Organization = apps.get_model("organization", "Organization")
            original_org = Organization.objects.filter(pk=self._original_organization_id).get()
            client.remove_user_from_group(
                self.cognito_username,
                OrganizationGroup(original_org.organization_id),
            )

        if self.organization_changed and self.organization:
            client.add_user_to_group(
                self.cognito_username,
                OrganizationGroup(self.organization.organization_id),
            )
        if self.unit_changed and self.unit:
            client.add_user_to_group(
                self.cognito_username,
                UnitGroup(self.unit.unit_id, self.organization.organization_id),
            )
        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    class Meta:
        proxy = True
        verbose_name = "Human User"
        verbose_name_plural = "Human Users"


class AccessRequest(models.Model):
    _context = "Access Request model"

    class AccessRequestState(models.TextChoices):
        """
        New access requests have state PENDING. An admin can either APPROVE or DECLINE
        an access request. The user can also CANCEL a pending access request.
        """

        PENDING = "PENDING", _("Access Request model", "Pending")
        APPROVED = "APPROVED", _("Access Request model", "Approved")
        DECLINED = "DECLINED", _("Access Request model", "Declined")
        CANCELLED = "CANCELLED", _("Access Request model", "Cancelled")

    access_request_id = CustomSlugField(
        _(_context, "Access Request ID"),
        max_length=100,
        unique=True,
        db_index=True,
        default=CustomSlugField.generate_unique_slug,
    )
    created = models.DateTimeField(_(_context, "Created"), auto_now_add=True)
    updated = models.DateTimeField(_(_context, "Updated"), auto_now=True)
    user = models.ForeignKey(HumanUser, on_delete=models.CASCADE)
    organization = models.ForeignKey("organization.Organization", on_delete=models.CASCADE)
    state = models.CharField(
        _(_context, "State"),
        max_length=20,
        choices=AccessRequestState.choices,
        default=AccessRequestState.PENDING,
    )

    def __str__(self) -> str:
        return self.access_request_id

    def save(
        self,
        *args: Any,  # noqa: ARG002 unused arguments
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:

        if self._state.adding:
            # Check user does not already have a pending access request
            if AccessRequest.objects.filter(
                user=self.user, state=AccessRequest.AccessRequestState.PENDING
            ).exists():
                raise ConflictError("User already has a pending access request")
            # Check user does not already belong to an organization
            if self.user.organization is not None:
                raise ConflictError("User already belongs to an organization")

        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
