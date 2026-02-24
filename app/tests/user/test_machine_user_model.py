from unittest.mock import patch

from django.core.exceptions import ValidationError

import pytest

from user.models import MachineUser


def test_object_stored_as_expected_for_valid_input(organization):
    machine_user_in = {
        "machine_user_id": "abc",
        "name": "Machine 1",
        "created_by_user": "user1",
        "organization": organization,
    }
    MachineUser.objects.create(**machine_user_in)

    machine_users = MachineUser.objects.all()

    assert len(machine_users) == 1

    actual = MachineUser.objects.last()
    assert actual is not None
    assert machine_user_in["machine_user_id"] == actual.machine_user_id
    assert machine_user_in["name"] == actual.name
    assert machine_user_in["created_by_user"] == actual.created_by_user
    assert machine_user_in["organization"] == actual.organization


def test_object_not_stored_for_invalid_input(machine_user, organization):
    machine_user_in = {
        "machine_user_id": "def",
        "name": "Machine 1",
        "created_by_user": "user1",
        "organization": organization,
    }
    with pytest.raises(ValidationError):
        MachineUser.objects.create(**machine_user_in)

    assert MachineUser.objects.count() == 1


@patch("user.models.Client")
@patch("user.extra_audience.Client")
def test_delete_deletes_records(ssm_client, boto_client, organization):
    model_fields = {
        "machine_user_id": "def",
        "name": "Machine 1",
        "created_by_user": "user1",
        "organization": organization,
    }

    MachineUser.objects.create(**model_fields)
    actual = MachineUser.objects.first()
    actual.delete()

    assert not MachineUser.objects.first()
    assert boto_client.return_value.delete_app_client.called
    assert ssm_client.return_value.get_parameter.called
    assert ssm_client.return_value.put_parameter.called
