from unittest.mock import patch

from user.models import CustomUser


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
    assert actual.last_name == "Machine 1"
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

    actual = CustomUser.objects.filter(user_type=CustomUser.UserType.MACHINE).first()
    actual.delete()

    assert not CustomUser.objects.filter(user_type=CustomUser.UserType.MACHINE).first()
    assert boto_client.return_value.delete_app_client.called
    assert ssm_client.return_value.get_parameter.called
    assert ssm_client.return_value.put_parameter.called
    assert avp_client.return_value.delete_policy.called
    assert avp_client.return_value.delete_policy.call_args.args[0] == "test-policy-id"
