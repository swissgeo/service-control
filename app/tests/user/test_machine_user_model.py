from unittest.mock import patch

import pytest

from organization.models import Organization, Unit
from user.models import CustomUser, MachineUser


@patch("user.models.VPClient")
def test_object_stored_as_expected_for_valid_input(
    avp_client, django_machine_user_factory, organization, user
):
    avp_client.return_value.create_machine_user_policy.return_value = "test-policy-id"
    machine_user_in = {
        "app_id": "abc",
        "name": "Machine 1",
        "created_by_user": user,
        "organization": organization,
    }
    django_machine_user_factory(**machine_user_in)

    machine_users = CustomUser.objects.filter(user_type=CustomUser.UserType.MACHINE).all()

    assert len(machine_users) == 1

    actual = CustomUser.objects.last()
    assert actual is not None
    assert actual.sub == "abc"
    assert actual.name == "Machine 1"
    assert machine_user_in["created_by_user"] == actual.created_by_user
    assert machine_user_in["organization"] == actual.organization
    assert actual.vp_machine_user_policy_id == "test-policy-id"

    assert avp_client.return_value.create_machine_user_policy.called


@patch("user.models.Client")
@patch("user.extra_audience.Client")
@patch("user.models.VPClient")
def test_delete_deletes_records(
    avp_client, ssm_client, boto_client, organization, user, django_machine_user_factory
):
    avp_client.return_value.create_machine_user_policy.return_value = "test-policy-id"
    model_fields = {
        "app_id": "def",
        "name": "Machine 1",
        "organization": organization,
        "created_by_user": user,
    }
    django_machine_user_factory(**model_fields)

    actual = MachineUser.objects.first()
    actual.delete()

    assert not MachineUser.objects.first()
    assert boto_client.return_value.delete_app_client.called
    assert ssm_client.return_value.get_parameter.called
    assert ssm_client.return_value.put_parameter.called
    assert avp_client.return_value.delete_policy.called
    assert avp_client.return_value.delete_policy.call_args.args[0] == "test-policy-id"


@patch("user.models.Client")
@patch("user.extra_audience.Client")
@patch("user.models.VPClient")
@patch("organization.models.VPClient")
def test_machine_user_cannot_change_org(
    vp_client, avp_client, ssm_client, boto_client, organization, user, django_machine_user_factory
):
    avp_client.return_value.create_machine_user_policy.return_value = "test-policy-id"
    vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id"
    vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
    vp_client.return_value.create_dataset_contributor_policy.return_value = (
        "mock-contributor-policy-id"
    )
    model_fields = {
        "app_id": "def",
        "name": "Machine 1",
        "organization": organization,
        "created_by_user": user,
    }
    django_machine_user_factory(**model_fields)

    actual = MachineUser.objects.first()
    actual.organization = Organization.objects.create(
        organization_id="other_id",
        acronym_de="Other",
        acronym_fr="Other",
        acronym_en="Other",
        name_de="Other",
        name_fr="Other",
        name_en="Other",
    )

    with pytest.raises(
        ValueError,
        match=(
            r"Changing organization or unit of a machine user is not allowed\. "
            r"Remove it and create a new one instead\."
        ),
    ):
        actual.save()


@patch("user.models.Client")
@patch("user.extra_audience.Client")
@patch("user.models.VPClient")
@patch("organization.models.VPClient")
def test_machine_user_cannot_change_unit(
    vp_client, avp_client, ssm_client, boto_client, organization, user, django_machine_user_factory
):
    avp_client.return_value.create_machine_user_policy.return_value = "test-policy-id"
    vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id"
    vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
    vp_client.return_value.create_dataset_contributor_policy.return_value = (
        "mock-contributor-policy-id"
    )
    model_fields = {
        "app_id": "def",
        "name": "Machine 1",
        "organization": organization,
        "created_by_user": user,
    }
    django_machine_user_factory(**model_fields)

    actual = MachineUser.objects.first()
    actual.unit = Unit.objects.create(
        unit_id="other_id",
        organization=organization,
        name_de="Other",
        name_fr="Other",
        name_en="Other",
    )

    with pytest.raises(
        ValueError,
        match=(
            r"Changing organization or unit of a machine user is not allowed\. "
            r"Remove it and create a new one instead\."
        ),
    ):
        actual.save()
