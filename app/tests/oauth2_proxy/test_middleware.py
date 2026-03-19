from unittest.mock import patch

from django.contrib.auth.models import Group

from user.models import CustomUser


@patch("user.models.Client")
def test_oauth_middleware_creates_user(cognito_client, settings, db, client):
    settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS = ["admin"]

    headers = {
        "HTTP_X_AUTH_REQUEST_USER": "hans.maulwurf",
        "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME": "cognito_hans",
        "HTTP_X_AUTH_REQUEST_EMAIL": "hans.maulwurf@example.com",
        "HTTP_X_AUTH_REQUEST_GROUPS": "admin",
        # Token parts base64 encoded:
        # Header:    {"alg": "HS256", "typ": "JWT"}
        # Payload:   {"first_name": "Hans", "last_name": "Maulwurf"}
        # Signature: invalid
        "HTTP_X_AUTH_REQUEST_ACCESS_TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmaXJzdF9uYW1lIjogIkhhbnMiLCAibGFzdF9uYW1lIjogIk1hdWx3dXJmIn0=.aW52YWxpZA==",  # noqa: E501
    }
    client.get("/", **headers)

    user = CustomUser.objects.get(sub="hans.maulwurf")
    assert user.email == "hans.maulwurf@example.com"
    assert user.first_name == "Hans"
    assert user.last_name == "Maulwurf"
    assert user.is_superuser
    assert user.is_staff
    assert user.cognito_username == "cognito_hans"


@patch("user.models.Client")
def test_oauth_middleware_updates_user(cognito_client, settings, db, client):
    settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS = ["admin"]

    CustomUser.objects.create(
        sub="joseph.quimby",
        first_name="Joe Quimby",
        email="joe.quimby@example.com",
        is_superuser=True,
        is_staff=True,
        user_type=CustomUser.UserType.HUMAN,
        cognito_username="cognito_joseph",
    )

    headers = {
        "HTTP_X_AUTH_REQUEST_USER": "joseph.quimby",
        "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME": "cognito_joseph",
        "HTTP_X_AUTH_REQUEST_EMAIL": "joseph.quimby@example.com",
        "HTTP_X_AUTH_REQUEST_GROUPS": "staff",
        # Token parts base64 encoded:
        # Header:    {"alg": "HS256", "typ": "JWT"}
        # Payload:   {"first_name": "Joseph", "last_name": "Quimby"}
        # Signature: invalid
        "HTTP_X_AUTH_REQUEST_ACCESS_TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmaXJzdF9uYW1lIjogIkpvc2VwaCIsICJsYXN0X25hbWUiOiAiUXVpbWJ5In0=.aW52YWxpZA==",  # noqa: E501
    }
    client.get("/", **headers)

    # Groups should not be created by middleware
    assert not Group.objects.filter(name="staff").exists()

    user = CustomUser.objects.get(sub="joseph.quimby")
    assert user.first_name == "Joseph"
    assert user.last_name == "Quimby"
    assert user.email == "joseph.quimby@example.com"
    assert not user.is_superuser
    assert not user.is_staff


@patch("user.models.Client")
def test_oauth_middleware_updated_superuser_staff(cognito_client, settings, db, client):
    settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS = ["admin"]
    CustomUser.objects.create(
        sub="joseph.quimby",
        cognito_username="cognito_joseph",
        first_name="Joseph",
        last_name="Quimby",
        email="joe.quimby@example.com",
        is_superuser=False,
        is_staff=False,
        user_type=CustomUser.UserType.HUMAN,
    )

    headers = {
        "HTTP_X_AUTH_REQUEST_USER": "joseph.quimby",
        "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME": "cognito_joseph",
        "HTTP_X_AUTH_REQUEST_EMAIL": "joseph.quimby@example.com",
        "HTTP_X_AUTH_REQUEST_GROUPS": "admin",
    }
    client.get("/", **headers)

    user = CustomUser.objects.get(sub="joseph.quimby")
    # Names should not be updated if token is missing
    assert user.first_name == "Joseph"
    assert user.last_name == "Quimby"
    assert user.email == "joseph.quimby@example.com"
    # values updated as user is in admin group
    assert user.is_superuser
    assert user.is_staff


@patch("user.models.Client")
def test_oauth_middleware_header_group_is_relevant(cognito_client, settings, db, client):
    # Test that the user is superuser/staff when the admin group is present in the header, even if
    # the user is not in the group. Normally this should not be possible in service-control. But in
    # other services that only rely on the headers/token and do not manage users this will be the
    # normal case.
    settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS = ["admin"]
    CustomUser.objects.create(
        sub="joseph.quimby",
        cognito_username="cognito_joseph",
        first_name="Joseph",
        last_name="Quimby",
        email="joe.quimby@example.com",
        is_superuser=False,
        is_staff=False,
        user_type=CustomUser.UserType.HUMAN,
    )

    headers = {
        "HTTP_X_AUTH_REQUEST_USER": "joseph.quimby",
        "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME": "cognito_joseph",
        "HTTP_X_AUTH_REQUEST_EMAIL": "joseph.quimby@example.com",
        "HTTP_X_AUTH_REQUEST_GROUPS": "admin",
    }
    client.get("/", **headers)

    user = CustomUser.objects.get(sub="joseph.quimby")
    assert user.first_name == "Joseph"
    assert user.last_name == "Quimby"
    assert user.email == "joseph.quimby@example.com"
    # values updated as user is in admin group
    assert user.is_superuser
    assert user.is_staff
