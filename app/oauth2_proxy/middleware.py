import logging
from typing import TYPE_CHECKING, cast

from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.contrib.auth.models import Group, User
from django.utils.deprecation import MiddlewareMixin

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)


class Oauth2ProxyRemoteUserMiddleware(RemoteUserMiddleware):
    header = "X_AUTH_REQUEST_USER"  # https://code.djangoproject.com/ticket/36300


class Oauth2ProxyRemoteMiddleware(MiddlewareMixin):
    group_header = "HTTP_X_AUTH_REQUEST_GROUPS"
    preferred_username_header = "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME"
    email_header = "HTTP_X_AUTH_REQUEST_EMAIL"

    def process_request(self, request: HttpRequest) -> None:  # noqa: C901
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        user = get_user(request)
        if not user.is_authenticated:
            # If the user is not authenticated then do nothing and let django
            # refuse the request
            return
        user = cast("User", user)

        # If the user is authenticated then we need to update it with the following oauth2-proxy
        # provided user information:
        #  - preferred_username
        #  - email
        #  - groups
        try:
            preferred_username = request.META[self.preferred_username_header].strip()
        except KeyError as error:
            logger.warning("Failed to get preferred_username header: %s", error)
            preferred_username = None

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

        for name in group_names:
            Group.objects.get_or_create(name=name)

        # Update the user in the DB. Only save if anything has changed to avoid writing to the DB
        # on every request.
        changed = False

        # Django user.first_name is used as display in the admin interface, therefore set it
        # to preferred user name.
        if preferred_username and user.first_name != preferred_username:
            user.first_name = preferred_username
            changed = True

        if email and user.email != email:
            user.email = email
            changed = True

        if raw_groups and {group.name for group in user.groups.all()} != set(group_names):
            user.groups.set(Group.objects.filter(name__in=group_names))

        # Check if the user is allowed in django admin interface
        is_admin = bool(set(group_names) & set(settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS))
        if is_admin != user.is_staff or is_admin != user.is_superuser:
            user.is_staff = is_admin
            user.is_superuser = is_admin
            changed = True

        if changed:
            user.save()
