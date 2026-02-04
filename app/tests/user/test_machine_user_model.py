from unittest.mock import patch

from asgiref.sync import async_to_sync

from django.core.exceptions import ValidationError as DjangoValidationError
from ninja.errors import ValidationError as NinjaValidationError

import pytest

from cognito.utils.client import CreateClientResponse
from user.models import MachineUser
from utils.testing import AsyncMagicMock


@patch("user.extra_audience.Client", new_callable=AsyncMagicMock)
@patch("user.models.Client", new_callable=AsyncMagicMock)
def test_object_stored_as_expected_for_valid_input(cognito_client, ssm_client, organization):
    cognito_client.return_value.create_app_client.return_value = CreateClientResponse(
        name="client_name",
        client_id="client_id",
        client_secret="client_secret",  # noqa: S106
    )

    machine_user_in = {
        "machine_user_id": "abc",
        "name": "Machine 1",
        "created_by_user": "user1",
        "organization": organization,
    }
    async_to_sync(MachineUser(**machine_user_in).save_and_sync)()

    machine_users = MachineUser.objects.all()

    assert len(machine_users) == 1

    actual = MachineUser.objects.last()
    assert actual is not None
    assert actual.machine_user_id == "client_id"
    assert machine_user_in["name"] == actual.name
    assert machine_user_in["created_by_user"] == actual.created_by_user
    assert machine_user_in["organization"] == actual.organization

    assert cognito_client.return_value.create_app_client.called
    assert ssm_client.return_value.put_parameter.called


@patch("user.extra_audience.Client", new_callable=AsyncMagicMock)
@patch("user.models.Client", new_callable=AsyncMagicMock)
def test_object_not_stored_for_invalid_input(
    cognito_client, ssm_client, machine_user, organization
):
    machine_user_in = {
        "machine_user_id": "def",
        "name": "Machine 1",
        "created_by_user": "user1",
        "organization": organization,
    }
    with pytest.raises(DjangoValidationError):
        async_to_sync(MachineUser(**machine_user_in).save_and_sync)()

    assert MachineUser.objects.count() == 1


@patch("user.extra_audience.Client", new_callable=AsyncMagicMock)
@patch("user.models.Client", new_callable=AsyncMagicMock)
def test_save_updates_records(cognito_client, ssm_client, organization, db):
    cognito_client.return_value.create_app_client.return_value = CreateClientResponse(
        name="client_name",
        client_id="client_id",
        client_secret="client_secret",  # noqa: S106
    )

    machine_user_in = {
        "machine_user_id": "abc",
        "name": "Machine 1",
        "created_by_user": "user1",
        "organization": organization,
    }
    async_to_sync(MachineUser(**machine_user_in).save_and_sync)()
    actual = MachineUser.objects.last()
    assert machine_user_in["name"] == actual.name
    assert cognito_client.return_value.create_app_client.called
    assert ssm_client.return_value.put_parameter.called

    cognito_client.return_value.reset_mock()
    ssm_client.return_value.reset_mock()
    actual.name = "Machine 2"
    async_to_sync(actual.save_and_sync)()
    updated = MachineUser.objects.first()
    assert updated.name == "Machine 2"
    assert cognito_client.return_value.mock_calls == []
    assert ssm_client.return_value.mock_calls == []

    actual.machine_user_id = "client_id_2"
    with pytest.raises(NinjaValidationError):
        async_to_sync(actual.save_and_sync)()

    assert MachineUser.objects.count() == 1
    assert cognito_client.return_value.mock_calls == []
    assert ssm_client.return_value.mock_calls == []


@patch("user.extra_audience.Client", new_callable=AsyncMagicMock)
@patch("user.models.Client", new_callable=AsyncMagicMock)
def test_delete_deletes_records(cognito_client, ssm_client, organization, db):
    ssm_client.return_value.get_parameter.return_value = "first,second"

    machine_user_in = {
        "machine_user_id": "abc",
        "name": "Machine 1",
        "created_by_user": "user1",
        "organization": organization,
    }
    async_to_sync(MachineUser(**machine_user_in).save_and_sync)()
    actual = MachineUser.objects.last()
    assert machine_user_in["name"] == actual.name
    assert cognito_client.return_value.create_app_client.called
    assert ssm_client.return_value.put_parameter.called

    async_to_sync(actual.delete_and_sync)()

    assert not MachineUser.objects.first()
    assert cognito_client.return_value.delete_app_client.called
    assert ssm_client.return_value.put_parameter.called
