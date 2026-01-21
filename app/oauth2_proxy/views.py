from urllib.parse import quote, quote_plus

from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


def base_url(request: HttpRequest) -> str:
    # Oauth2-proxy should always be reached from the same domain as django,
    # because it is configured with session cookie domain lock.
    return request.build_absolute_uri("/")


def admin_login(request: HttpRequest) -> HttpResponse:
    # Redirect URL after successful login
    redirect_uri = f"{request.build_absolute_uri(reverse('admin:index'))}"

    oauth2_proxy_login_url = (
        f"{base_url(request)}{settings.OAUTH2_PROXY_URL_PREFIX}start?rd={quote(redirect_uri)}"
    )

    return redirect(oauth2_proxy_login_url)


def admin_logout(request: HttpRequest) -> HttpResponse:
    # logout the user from Django
    logout(request)

    # Redirect to the base page after logout
    redirect_after_logout = base_url(request)

    # We need to log out (chained with redirects) from eIAM, Cognito and OAuth2 Proxy
    eiam_logout_url = (
        f"{settings.OAUTH2_PROXY_EIAM_LOGOUT_URL}?"
        f"post_logout_redirect_uri={quote_plus(redirect_after_logout)}"
    )

    cognito_logout_url = (
        f"{settings.OAUTH2_PROXY_COGNITO_URL}/logout?"
        f"client_id={settings.OAUTH2_PROXY_COGNITO_APP_CLIENT_ID}&"
        f"logout_uri={quote_plus(eiam_logout_url)}"
    )

    oauth_proxy_logout_url = (
        f"{base_url(request)}{settings.OAUTH2_PROXY_URL_PREFIX}sign_out?"
        f"rd={quote_plus(cognito_logout_url)}"
    )

    return redirect(oauth_proxy_logout_url)
