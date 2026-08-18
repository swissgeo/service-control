import logging
from collections.abc import Callable
from typing import cast

import jwt

from django.conf import settings
from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.http import HttpRequest, HttpResponse
from ninja.errors import AuthenticationError

from user.models import CustomUser

logger = logging.getLogger(__name__)


class RemoteCustomUserBackend(RemoteUserBackend):
    """Middleware backend to create a CustomUser when a new user is created."""

    preferred_username_header = "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME"

    def configure_user(
        self, request: HttpRequest | None, user: CustomUser, created: bool = True
    ) -> CustomUser:
        """
        If a new user was created, add the cognito_username with the value from the
        preferred_username from the header.
        Only human users are created here when they login for the first time. Machine users are
        created separately. Machine users will also never have a cognito_username.
        """
        if created:
            if cognito_username := getattr(request, "META", {}).get(self.preferred_username_header):
                user.cognito_username = cognito_username
                user.save()
            else:
                logger.error("Failed to get preferred_username header")
                raise AuthenticationError
        return user


class Oauth2ProxyRemoteUserMiddleware(RemoteUserMiddleware):
    header = "HTTP_X_AUTH_REQUEST_USER"


class Oauth2ProxyRemoteMiddleware:
    """
    Middleware Checks if user is authenticated and returns if not.

    For machine users, nothing else is done as they don't have any profile information.

    For human users update their profile information for email, first_name and last_name. This
    information comes from Cognito and is provided in the headers/access token. As cognito is the
    "data-owner" for these attributes, we always update these values in service-control.
    Next read the user groups and check if the user is superuser/staff. This is a special group
    that allows the user to access the admin UI. Groups are not updated based as cognito is not the
    "data-owner", but service-control. If users groups change this must be done via service-control
    that will update cognito accordingly.
    The same goes for the users roles. They are not updated from the token as service-control is the
    "data-owner" for roles. Roles are not read in this middleware as they are not needed at this
    level. They will be checked on endpoints level checks where needed.
    """

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

        user = request.user  # this is set by the middleware above
        if not user.is_authenticated:
            # If the user is not authenticated then do nothing and let django
            # refuse the request
            return self.get_response(request)
        user = cast("CustomUser", user)

        if user.user_type == CustomUser.UserType.HUMAN:
            self._update_user_profile(request, user)

        return self.get_response(request)

    def _update_user_profile(self, request: HttpRequest, user: CustomUser) -> bool:
        """
        Update the user profile with the information from the token and headers.
        Returns True if the user was updated, False otherwise.
        """
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
        return changed
