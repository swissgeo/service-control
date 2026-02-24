import logging
from typing import TYPE_CHECKING, cast

import jwt

from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.auth.middleware import RemoteUserMiddleware

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.contrib.auth.models import User
    from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class Oauth2ProxyRemoteUserMiddleware(RemoteUserMiddleware):
    header = "HTTP_X_AUTH_REQUEST_USER"


class Oauth2ProxyRemoteMiddleware:
    group_header = "HTTP_X_AUTH_REQUEST_GROUPS"
    preferred_username_header = "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME"
    email_header = "HTTP_X_AUTH_REQUEST_EMAIL"
    token_header = "HTTP_X_AUTH_REQUEST_ACCESS_TOKEN"  # noqa: S105 possible hardcoded password

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        user = get_user(request)
        if not user.is_authenticated:
            # If the user is not authenticated then do nothing and let django
            # refuse the request
            return self.get_response(request)
        user = cast("User", user)

        # If the user is authenticated then we need to update it with the following oauth2-proxy
        # provided user information:
        #  - email
        #  - first_name
        #  - last_name
        #
        # Groups are not updated from oauth2-proxy as service-control is the data-owner for groups.
        # Any changes to groups will always be done via service-control

        try:
            email = request.META[self.email_header].strip()
        except KeyError as error:
            logger.warning("Failed to get email header: %s", error)
            email = None

        try:
            raw_groups = request.META[self.group_header]
        except KeyError as error:
            logger.warning("Failed to get group header: %s", error)
            raw_groups = ""

        group_names = [g.strip() for g in raw_groups.split(",") if g.strip()]

        try:
            token = request.META[self.token_header].strip()
            # As oauth2-proxy already verifies the token, we skip verification and only read payload
            # This is also important for performance as validating signature would require a call to
            # cognito to retrieve the public key.
            decoded = jwt.decode(token, options={"verify_signature": False})
            first_name = decoded["first_name"]
            last_name = decoded["last_name"]
        except KeyError as error:
            logger.warning("Failed to get token header: %s", error)
            first_name = ""
            last_name = ""

        # Update the user in the DB. Only save if anything has changed to avoid writing to the DB
        # on every request.
        changed = False

        if first_name and user.first_name != first_name:
            user.first_name = first_name
            changed = True
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            changed = True
        if email and user.email != email:
            user.email = email
            changed = True

        # Check if the user is allowed in django admin interface
        is_admin = bool(set(group_names) & set(settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS))
        if is_admin != user.is_staff or is_admin != user.is_superuser:
            user.is_staff = is_admin
            user.is_superuser = is_admin
            changed = True

        if changed:
            user.save()

        return self.get_response(request)
