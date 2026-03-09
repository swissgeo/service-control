from typing import TYPE_CHECKING

from django.http import HttpRequest  # noqa:TC002
from ninja.errors import AuthorizationError

from organization.models import Organization, Unit
from user.models import CustomUser
from verified_permissions.utils.client import Client

if TYPE_CHECKING:
    from collections.abc import Callable


def vp_auth(action: str, path_var: str = "organization_id") -> Callable[[HttpRequest], bool]:
    """
    Checks if the user is logged in and has the required permissions for the action.
    """
    token_header = "HTTP_X_AUTH_REQUEST_ACCESS_TOKEN"  # noqa: S105 possible hardcoded password
    client = Client()

    def validation(request: HttpRequest) -> bool:
        if not request.user.is_authenticated:
            return False

        # is_superuser is defined on PermissionsMixin,
        # not AbstractBaseUser (should be present though)
        if getattr(request.user, "is_superuser", False):
            return True

        token = request.META[token_header]
        if (resolver_match := request.resolver_match) and resolver_match.kwargs.get(path_var):
            resource = _get_resource(path_var, request)
            if resource and client.is_authorized(token=token, action=action, resource=resource):
                return True

        raise AuthorizationError

    return validation


def _get_resource(path_var: str, request: HttpRequest) -> Organization | Unit | CustomUser | None:
    if (resolver_match := request.resolver_match) and resolver_match.kwargs.get(path_var):
        object_id = resolver_match.kwargs.get(path_var)
        if path_var == "organization_id":
            return Organization.objects.filter(organization_id=object_id).first()
        if path_var == "unit_id":
            return Unit.objects.filter(unit_id=object_id).first()
        if path_var == "machine_user_id":
            return CustomUser.objects.filter(username=object_id).first()
    return None


def role_auth(required_role: str) -> Callable[[HttpRequest], bool]:
    """
    Checks if the user is logged in and has the required role.
    """

    def validation(request: HttpRequest) -> bool:
        if not request.user.is_authenticated:
            return False

        # is_superuser is defined on PermissionsMixin,
        # not AbstractBaseUser (should be present though)
        if getattr(request.user, "is_superuser", False):
            return True

        custom_user = getattr(request.user, "customuser", None)
        if custom_user and custom_user.roles and required_role in custom_user.roles:
            return True

        raise AuthorizationError

    return validation


def organization_role_auth(
    required_role: str, path_var: str = "organization_id"
) -> Callable[[HttpRequest], bool]:
    """
    Checks if the user is logged in and has the required role and the organization matches the
    organization in the request path.
    """

    def validation(request: HttpRequest) -> bool:
        if not request.user.is_authenticated:
            return False

        # is_superuser is defined on PermissionsMixin,
        # not AbstractBaseUser (should be present though)
        if getattr(request.user, "is_superuser", False):
            return True

        custom_user = getattr(request.user, "customuser", None)
        if (
            (custom_user := getattr(request.user, "customuser", None))
            and (resolver_match := request.resolver_match)
            and custom_user.organization.organization_id == resolver_match.kwargs.get(path_var)
            and custom_user.roles
            and required_role in custom_user.roles
        ):
            return True

        raise AuthorizationError

    return validation


def superuser_auth(request: HttpRequest) -> bool:
    """
    Checks if the user is logged in as superuser.
    """
    if not request.user.is_authenticated:
        return False

    # is_superuser is defined on PermissionsMixin, not AbstractBaseUser (should be present though)
    if getattr(request.user, "is_superuser", False):
        return True

    raise AuthorizationError
