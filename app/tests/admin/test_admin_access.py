from django.conf import settings


def test_admin_access_not_authenticated(client):
    response = client.get("/admin/")
    assert response.status_code == 302
    assert response.headers["Location"] == "/admin/login/?next=/admin/"
    response = client.get(response.headers["Location"])
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "Log in | Django site admin" in response.text
    assert "Login via OAuth2" in response.text


def test_admin_access_authenticated_not_allowed(client, db):
    response = client.get(
        "/admin/",
        HTTP_X_AUTH_REQUEST_USER="test",
        HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME="test",
        HTTP_X_AUTH_REQUEST_EMAIL="test@example.com",
        HTTP_X_AUTH_REQUEST_GROUPS="not-allowed",
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/admin/login/?next=/admin/"
    response = client.get(
        response.headers["Location"],
        HTTP_X_AUTH_REQUEST_USER="test",
        HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME="test",
        HTTP_X_AUTH_REQUEST_EMAIL="test@example.com",
        HTTP_X_AUTH_REQUEST_GROUPS="not-allowed",
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert (
        "You are authenticated as test, but are not authorized to access this page."
        in response.text
    )


def test_admin_access_authenticated_allowed(client, db):
    response = client.get(
        "/admin/",
        HTTP_X_AUTH_REQUEST_USER="test",
        HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME="test",
        HTTP_X_AUTH_REQUEST_EMAIL="test@example.com",
        HTTP_X_AUTH_REQUEST_GROUPS=settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS[0],
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "Site administration | Django site admin" in response.text
