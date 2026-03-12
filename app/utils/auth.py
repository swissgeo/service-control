from typing import TYPE_CHECKING

from django.http import HttpRequest  # noqa:TC002
from ninja.errors import AuthorizationError

from utils import api_path
from verified_permissions.utils.client import Client

if TYPE_CHECKING:
    from collections.abc import Callable

    from config.authorization import VPAction
    from utils.api_path import Parameter
    from verified_permissions.utils.base import BaseClient


class _VPClientCache:
    instance: BaseClient | None = None


def _get_vp_client() -> BaseClient:
    if _VPClientCache.instance is None:
        _VPClientCache.instance = Client()
    return _VPClientCache.instance


def vp_auth(
    action: VPAction, resource: Parameter = api_path.Organization
) -> Callable[[HttpRequest], bool]:
    """
    Checks if the user is logged in and has the required permissions for the action.
    """
    token_header = "HTTP_X_AUTH_REQUEST_ACCESS_TOKEN"  # noqa: S105 possible hardcoded password

    def validation(request: HttpRequest) -> bool:
        if not request.user.is_authenticated:
            return False

        # is_superuser is defined on PermissionsMixin,
        # not AbstractBaseUser (should be present though)
        if getattr(request.user, "is_superuser", False):
            return True

        client = _get_vp_client()
        token = request.META[token_header]
        if client.is_authorized(
            token=token, action=action.value, resource=resource, request=request
        ):
            return True

        raise AuthorizationError

    return validation


def is_authenticated(request: HttpRequest) -> bool:
    """
    Checks if the user is logged in.
    """
    return request.user.is_authenticated


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
