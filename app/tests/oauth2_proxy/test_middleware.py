from django.contrib.auth.models import Group


def test_oauth_middleware_creates_user(settings, db, client, django_user_model):
    settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS = ["admin"]

    headers = {
        "X_AUTH_REQUEST_USER": "hans.maulwurf",
        "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME": "Hans Maulwurf",
        "HTTP_X_AUTH_REQUEST_EMAIL": "hans.maulwurf@example.com",
        "HTTP_X_AUTH_REQUEST_GROUPS": "admin",
    }
    client.get("/", **headers)

    assert Group.objects.filter(name="admin").exists()

    user = django_user_model.objects.get(username="hans.maulwurf")
    assert user.first_name == "Hans Maulwurf"
    assert user.email == "hans.maulwurf@example.com"
    assert user.is_superuser
    assert user.is_staff
    assert user.groups.filter(name="admin").exists()


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
        "X_AUTH_REQUEST_USER": "joseph.quimby",
        "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME": "Joseph Quimby",
        "HTTP_X_AUTH_REQUEST_EMAIL": "joseph.quimby@example.com",
        "HTTP_X_AUTH_REQUEST_GROUPS": "staff",
    }
    client.get("/", **headers)

    assert Group.objects.filter(name="staff").exists()

    user = django_user_model.objects.get(username="joseph.quimby")
    assert user.first_name == "Joseph Quimby"
    assert user.email == "joseph.quimby@example.com"
    assert not user.is_superuser
    assert not user.is_staff
    assert user.groups.filter(name="staff").exists()
    assert not user.groups.filter(name="admin").exists()
