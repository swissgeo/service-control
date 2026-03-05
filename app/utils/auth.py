from typing import TYPE_CHECKING

from django.http import HttpRequest  # noqa:TC002
from ninja.errors import AuthorizationError

if TYPE_CHECKING:
    from collections.abc import Callable


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
