from django.contrib.auth.models import Group


def test_oauth_middleware_creates_user(settings, db, client, django_user_model):
    settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS = ["admin"]

    headers = {
        "HTTP_X_AUTH_REQUEST_USER": "hans.maulwurf",
        "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME": "hans.maulwurf",
        "HTTP_X_AUTH_REQUEST_EMAIL": "hans.maulwurf@example.com",
        "HTTP_X_AUTH_REQUEST_GROUPS": "admin",
        # Token parts base64 encoded:
        # Header:    {"alg": "HS256", "typ": "JWT"}
        # Payload:   {"first_name": "Hans", "last_name": "Maulwurf"}
        # Signature: invalid
        "HTTP_X_AUTH_REQUEST_TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmaXJzdF9uYW1lIjogIkhhbnMiLCAibGFzdF9uYW1lIjogIk1hdWx3dXJmIn0=.aW52YWxpZA==",  # noqa: E501
    }
    client.get("/", **headers)

    user = django_user_model.objects.get(username="hans.maulwurf")
    assert user.username == "hans.maulwurf"
    assert user.email == "hans.maulwurf@example.com"
    assert user.first_name == "Hans"
    assert user.last_name == "Maulwurf"
    assert user.is_superuser
    assert user.is_staff
    # User groups should not be updated/created with values from proxy.
    assert not user.groups.filter(name="admin").exists()


def test_oauth_middleware_updates_user(settings, db, client, django_user_model):
    settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS = ["admin"]

    group = Group.objects.create(name="admin")

    user = django_user_model.objects.create_user(
        username="joseph.quimby",
        password="pass",  # noqa: S106
    )
    user.first_name = "Joe Quimby"
    user.email = "joe.quimby@example.com"
    user.is_superuser = True
    user.is_staff = True
    user.groups.add(group)
    user.save()

    headers = {
        "HTTP_X_AUTH_REQUEST_USER": "joseph.quimby",
        "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME": "joseph.quimby",
        "HTTP_X_AUTH_REQUEST_EMAIL": "joseph.quimby@example.com",
        "HTTP_X_AUTH_REQUEST_GROUPS": "staff",
        # Token parts base64 encoded:
        # Header:    {"alg": "HS256", "typ": "JWT"}
        # Payload:   {"first_name": "Joseph", "last_name": "Quimby"}
        # Signature: invalid
        "HTTP_X_AUTH_REQUEST_TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmaXJzdF9uYW1lIjogIkpvc2VwaCIsICJsYXN0X25hbWUiOiAiUXVpbWJ5In0=.aW52YWxpZA==",  # noqa: E501
    }
    client.get("/", **headers)

    # Groups should not be created by middleware
    assert not Group.objects.filter(name="staff").exists()

    user = django_user_model.objects.get(username="joseph.quimby")
    assert user.first_name == "Joseph"
    assert user.last_name == "Quimby"
    assert user.email == "joseph.quimby@example.com"
    assert not user.is_superuser
    assert not user.is_staff
    # User groups should not be updated by middleware
    assert not user.groups.filter(name="staff").exists()
    assert user.groups.filter(name="admin").exists()


def test_oauth_middleware_updated_superuser_staff(settings, db, client, django_user_model):
    settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS = ["admin"]

    group = Group.objects.create(name="admin")

    user = django_user_model.objects.create_user(
        username="joseph.quimby",
        password="pass",  # noqa: S106
    )
    user.first_name = "Joseph"
    user.last_name = "Quimby"
    user.email = "joe.quimby@example.com"
    user.is_superuser = False
    user.is_staff = False
    user.groups.add(group)
    user.save()

    headers = {
        "HTTP_X_AUTH_REQUEST_USER": "joseph.quimby",
        "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME": "joseph.quimby",
        "HTTP_X_AUTH_REQUEST_EMAIL": "joseph.quimby@example.com",
        "HTTP_X_AUTH_REQUEST_GROUPS": "admin",
    }
    client.get("/", **headers)

    user = django_user_model.objects.get(username="joseph.quimby")
    # Names should not be updated if token is missing
    assert user.first_name == "Joseph"
    assert user.last_name == "Quimby"
    assert user.email == "joseph.quimby@example.com"
    # values updated as user is in admin group
    assert user.is_superuser
    assert user.is_staff
    assert user.groups.filter(name="admin").exists()
