from django.http import HttpRequest  # noqa:TC002
from ninja.errors import AuthorizationError


def any_organization_admin_auth(request: HttpRequest) -> bool:
    """
    Checks if the user is logged in as superuser or organization admin.
    Does not check for which organization.

    # TODO: only for admin
    # TODO: Depending on how we implement the role check, this may function may
    not be needed anymore.
    """
    if not request.user.is_authenticated:
        return False

    # is_superuser is defined on PermissionsMixin, not AbstractBaseUser (should be present though)
    if getattr(request.user, "is_superuser", False):
        return True

    if getattr(request.user, "customuser", None) is not None:
        return True

    raise AuthorizationError


def organization_admin_auth(request: HttpRequest) -> bool:
    """
    Checks if the user is logged in as superuser or organization admin for the organization
    requested by url path.

    # TODO: only for admin
    """
    if not request.user.is_authenticated:
        return False

    # is_superuser is defined on PermissionsMixin, not AbstractBaseUser (should be present though)
    if getattr(request.user, "is_superuser", False):
        return True

    if (
        (custom_user := getattr(request.user, "customuser", None))
        and (resolver_match := request.resolver_match)
        and custom_user.organization.organization_id == resolver_match.kwargs.get("organization_id")
    ):
        return True

    raise AuthorizationError


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
