# Import mock_api to register its test routes on the shared `api` instance.
# mock_api uses api.add_router() as a side effect at import time, so it must
# be imported before any test client request is made.
import tests.config.mock_api  # noqa: F401


def test_handle_404_not_found(client):
    response = client.get("/api/v1/trigger-not-found")
    assert response.status_code == 404
    assert response.json() == {"code": 404, "description": "Resource not found"}


def test_handle_does_not_exist(client, db):
    response = client.get("/api/v1/trigger-does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"code": 404, "description": "Resource not found"}


def test_handle_http_error(client):
    response = client.get("/api/v1/trigger-http-error")
    assert response.status_code == 303
    assert response.json() == {"code": 303, "description": "See other"}


def test_handle_ninja_validation_error(client):
    response = client.get("/api/v1/trigger-ninja-validation-error")
    assert response.status_code == 400
    assert response.json() == {"code": 400, "description": ["Not a valid email."]}


def test_handle_unauthorized(client):
    response = client.get("/api/v1/trigger-authentication-error")
    assert response.status_code == 401
    assert response.json() == {"code": 401, "description": "Unauthorized"}


def test_handle_exception(client):
    response = client.get("/api/v1/trigger-internal-server-error")
    assert response.status_code == 500
    assert response.json() == {"code": 500, "description": "Internal Server Error"}


def test_handle_django_validation_error(client):
    response = client.get("/api/v1/trigger-django-validation-error")
    assert response.status_code == 400
    assert response.json() == {"code": 400, "description": ["Not a valid email."]}


def test_handle_conflict_error(client):
    response = client.get("/api/v1/trigger-conflict-error")
    assert response.status_code == 409
    assert response.json() == {"code": 409, "description": "Conflict Error"}
