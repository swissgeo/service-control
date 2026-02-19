from unittest.mock import patch

from cognito.utils.client import CreateClientResponse
from utils.testing import AsyncMagicMock


def test_get_machine_users_returns_expected(machine_user, client):
    response = client.get(
        f"/api/v1/organizations/{machine_user.organization.organization_id}/machineusers"
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "name": machine_user.name,
                "client_id": machine_user.machine_user_id,
            }
        ]
    }


@patch("user.models.Client", new_callable=AsyncMagicMock)
@patch("user.extra_audience.Client", new_callable=AsyncMagicMock)
def test_create_machine_user(ssm_client, boto_client, machine_user, client):
    mock_client = CreateClientResponse(name="machine name", client_id="xyz", client_secret="asdf")  # noqa: S106
    boto_client.return_value.create_app_client.return_value = mock_client
    data = {
        "name": "machine name",
    }
    response = client.post(
        f"/api/v1/organizations/{machine_user.organization.organization_id}/machineusers",
        content_type="application/json",
        data=data,
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


@patch("user.models.Client", new_callable=AsyncMagicMock)
@patch("user.extra_audience.Client", new_callable=AsyncMagicMock)
def test_create_machine_user_fails_if_already_exists(ssm_client, boto_client, machine_user, client):
    mock_client = CreateClientResponse(name="Machine 1", client_id="xyz", client_secret="asdf")  # noqa: S106
    boto_client.return_value.create_app_client.return_value = mock_client
    data = {
        "name": "Machine 1",
    }
    response = client.post(
        f"/api/v1/organizations/{machine_user.organization.organization_id}/machineusers",
        content_type="application/json",
        data=data,
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": 422,
        "description": ["machine user with this name already exists"],
    }
    assert boto_client.return_value.create_app_client.call_count == 1
    assert boto_client.return_value.delete_app_client.call_count == 1
    assert ssm_client.return_value.mock_calls == []


@patch("user.signals.Client", new_callable=AsyncMagicMock)
@patch("user.extra_audience.Client", new_callable=AsyncMagicMock)
def test_delete_machine_user(ssm_client, boto_client, machine_user, client):
    ssm_client.return_value.get_parameter.return_value = ""

    response = client.delete(
        f"/api/v1/organizations/{machine_user.organization.organization_id}/machineusers/{machine_user.machine_user_id}",
    )

    assert response.status_code == 204
    assert boto_client.return_value.delete_app_client.call_count == 1
    assert ssm_client.return_value.get_parameter.call_count == 1
    assert ssm_client.return_value.put_parameter.call_count == 1
