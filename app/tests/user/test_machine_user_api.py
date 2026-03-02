from unittest.mock import patch

import pytest

from cognito.utils.client import CreateClientResponse

# ==========  GET  ==========


@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401), ("user", 403)])
def test_get_machine_users_unauthorized(username, status_code, user_headers, machine_user, client):
    response = client.get(
        f"/api/v1/organizations/{machine_user.organization.organization_id}/machineusers",
        headers=user_headers[username],
    )

    assert response.status_code == status_code


@pytest.mark.parametrize("username", ["admin", "organization_admin"])
def test_get_machine_users_returns_expected(username, user_headers, machine_user, client):
    response = client.get(
        f"/api/v1/organizations/{machine_user.organization.organization_id}/machineusers",
        headers=user_headers[username],
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "name": machine_user.user.last_name,
                "client_id": machine_user.user.username,
            }
        ]
    }


# ==========  POST  ==========


@patch("user.api.Client")
@patch("user.extra_audience.Client")
@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401), ("user", 403)])
def test_create_machine_user_unauthorized(
    ssm_client, boto_client, username, status_code, user_headers, machine_user, client
):
    response = client.post(
        f"/api/v1/organizations/{machine_user.organization.organization_id}/machineusers",
        content_type="application/json",
        headers=user_headers[username],
        data={"name": "machine name"},
    )

    assert response.status_code == status_code
    assert not boto_client.return_value.create_app_client.called
    assert not ssm_client.return_value.get_parameter.called
    assert not ssm_client.return_value.put_parameter.called


@patch("user.api.Client")
@patch("user.extra_audience.Client")
@pytest.mark.parametrize("username", ["admin", "organization_admin"])
def test_create_machine_user_creates_as_expected(
    ssm_client, boto_client, username, user_headers, machine_user, client
):
    mock_client = CreateClientResponse(name="machine name", client_id="xyz", client_secret="asdf")
    boto_client.return_value.create_app_client.return_value = mock_client

    response = client.post(
        f"/api/v1/organizations/{machine_user.organization.organization_id}/machineusers",
        content_type="application/json",
        headers=user_headers[username],
        data={"name": "machine name"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "name": mock_client.name,
        "client_id": mock_client.client_id,
        "client_secret": mock_client.client_secret,
    }
    assert boto_client.return_value.create_app_client.call_count == 1
    assert ssm_client.return_value.get_parameter.call_count == 1
    assert ssm_client.return_value.put_parameter.call_count == 1


@patch("user.api.Client")
@patch("user.extra_audience.Client")
def test_create_machine_user_fails_if_already_exists(
    ssm_client, boto_client, machine_user, client, user_headers
):
    mock_client = CreateClientResponse(name="Machine 1", client_id="xyz", client_secret="asdf")
    boto_client.return_value.create_app_client.return_value = mock_client

    response = client.post(
        f"/api/v1/organizations/{machine_user.organization.organization_id}/machineusers",
        content_type="application/json",
        headers=user_headers["admin"],
        data={"name": "Machine 1"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": 422,
        "description": ["machine user with this name already exists"],
    }
    assert boto_client.return_value.mock_calls == []
    assert ssm_client.return_value.mock_calls == []


# ==========  DELETE  ==========


@patch("user.models.Client")
@patch("user.extra_audience.Client")
@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401), ("user", 403)])
def test_delete_machine_user_unauthorized(
    ssm_client, boto_client, username, status_code, user_headers, machine_user, client
):
    response = client.delete(
        f"/api/v1/organizations/{machine_user.organization.organization_id}/machineusers/{machine_user.user.username}",
        headers=user_headers[username],
    )

    assert response.status_code == status_code
    assert not boto_client.return_value.delete_app_client.call_count
    assert not ssm_client.return_value.get_parameter.call_count
    assert not ssm_client.return_value.put_parameter.call_count


@patch("user.models.Client")
@patch("user.extra_audience.Client")
@pytest.mark.parametrize("username", ["admin", "organization_admin"])
def test_delete_machine_user_deletes_as_expected(
    ssm_client, boto_client, username, user_headers, machine_user, client
):
    response = client.delete(
        f"/api/v1/organizations/{machine_user.organization.organization_id}/machineusers/{machine_user.user.username}",
        headers=user_headers[username],
    )

    assert response.status_code == 204
    assert boto_client.return_value.delete_app_client.call_count == 1
    assert ssm_client.return_value.get_parameter.call_count == 1
    assert ssm_client.return_value.put_parameter.call_count == 1
