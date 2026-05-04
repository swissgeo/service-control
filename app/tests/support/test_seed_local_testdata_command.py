from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from support.management.commands.seed_local_testdata import USERS


def _seed_usernames() -> list[str]:
    return [user["username"] for user in USERS]


def _seed_subs() -> list[str]:
    return [user["sub"] for user in USERS]


def _org_member_count() -> int:
    return sum(1 for user in USERS if user["organization_id"] is not None)


def _user_update_side_effect() -> list[tuple[SimpleNamespace, bool]]:
    return [(SimpleNamespace(cognito_username=username), True) for username in _seed_usernames()]


def _admin_get_user_side_effect() -> list[dict[str, list[dict[str, str]]]]:
    return [{"UserAttributes": [{"Name": "sub", "Value": sub}]} for sub in _seed_subs()]


@patch("support.management.commands.seed_local_testdata.CognitoClient")
@patch("support.management.commands.seed_local_testdata.HumanUser")
@patch("support.management.commands.seed_local_testdata.Organization")
def test_seed_local_testdata(mock_organization, mock_human_user, mock_cognito_client):
    org_records = {
        "ch.bafu": SimpleNamespace(organization_id="ch.bafu"),
        "ch.swisstopo": SimpleNamespace(organization_id="ch.swisstopo"),
    }

    org_update_or_create = MagicMock(
        side_effect=[
            (org_records["ch.bafu"], True),
            (org_records["ch.swisstopo"], True),
        ]
    )
    user_update_or_create = MagicMock(side_effect=_user_update_side_effect())

    fake_cognito = MagicMock()
    fake_cognito.user_pool_id = "local"
    fake_cognito.client.admin_get_user.side_effect = _admin_get_user_side_effect()

    mock_organization.objects.update_or_create = org_update_or_create
    mock_human_user.objects.update_or_create = user_update_or_create
    mock_cognito_client.return_value = fake_cognito

    out = StringIO()
    call_command("seed_local_testdata", verbosity=2, stdout=out)
    output = out.getvalue()

    assert f"Seeded 2 organizations and {len(USERS)} users" in output
    assert org_update_or_create.call_count == 2
    assert user_update_or_create.call_count == len(USERS)
    assert fake_cognito.client.admin_add_user_to_group.call_count == _org_member_count()
    assert fake_cognito.update_user_roles.call_count == len(USERS)


@patch("support.management.commands.seed_local_testdata.CognitoClient")
@patch("support.management.commands.seed_local_testdata.HumanUser")
@patch("support.management.commands.seed_local_testdata.Organization")
def test_seed_local_testdata_with_reset(mock_organization, mock_human_user, mock_cognito_client):
    org_records = {
        "ch.bafu": SimpleNamespace(organization_id="ch.bafu"),
        "ch.swisstopo": SimpleNamespace(organization_id="ch.swisstopo"),
    }

    org_update_or_create = MagicMock(
        side_effect=[
            (org_records["ch.bafu"], True),
            (org_records["ch.swisstopo"], True),
        ]
    )
    org_filter_delete = MagicMock(return_value=(1, {}))

    user_update_or_create = MagicMock(side_effect=_user_update_side_effect())
    user_filter_delete = MagicMock(return_value=(1, {}))

    fake_cognito = MagicMock()
    fake_cognito.user_pool_id = "local"
    fake_cognito.client.admin_get_user.side_effect = _admin_get_user_side_effect()

    mock_organization.objects.update_or_create = org_update_or_create
    mock_organization.objects.filter.return_value.delete = org_filter_delete
    mock_human_user.objects.update_or_create = user_update_or_create
    mock_human_user.objects.filter.return_value.delete = user_filter_delete
    mock_cognito_client.return_value = fake_cognito

    out = StringIO()
    call_command("seed_local_testdata", "--reset", verbosity=2, stdout=out)
    output = out.getvalue()

    assert "Reset complete, applying seed data" in output
    assert user_filter_delete.call_count == len(USERS)
    assert org_filter_delete.call_count == 2
    assert fake_cognito.client.admin_delete_user.call_count == 0
    assert org_update_or_create.call_count == 2
    assert user_update_or_create.call_count == len(USERS)


@patch("support.management.commands.seed_local_testdata.CognitoClient")
@patch("support.management.commands.seed_local_testdata.HumanUser")
@patch("support.management.commands.seed_local_testdata.Organization")
def test_seed_local_testdata_with_reset_and_cognito_recreate(
    mock_organization,
    mock_human_user,
    mock_cognito_client,
):
    org_records = {
        "ch.bafu": SimpleNamespace(organization_id="ch.bafu"),
        "ch.swisstopo": SimpleNamespace(organization_id="ch.swisstopo"),
    }

    org_update_or_create = MagicMock(
        side_effect=[
            (org_records["ch.bafu"], True),
            (org_records["ch.swisstopo"], True),
        ]
    )
    org_filter_delete = MagicMock(return_value=(1, {}))

    user_update_or_create = MagicMock(side_effect=_user_update_side_effect())
    user_filter_delete = MagicMock(return_value=(1, {}))

    fake_cognito = MagicMock()
    fake_cognito.user_pool_id = "local"
    fake_cognito.client.admin_get_user.side_effect = _admin_get_user_side_effect()

    mock_organization.objects.update_or_create = org_update_or_create
    mock_organization.objects.filter.return_value.delete = org_filter_delete
    mock_human_user.objects.update_or_create = user_update_or_create
    mock_human_user.objects.filter.return_value.delete = user_filter_delete
    mock_cognito_client.return_value = fake_cognito

    out = StringIO()
    call_command(
        "seed_local_testdata",
        "--reset",
        "--recreate-cognito-users",
        verbosity=2,
        stdout=out,
    )

    assert user_filter_delete.call_count == len(USERS)
    assert org_filter_delete.call_count == 2
    assert fake_cognito.client.admin_delete_user.call_count == len(USERS)
    assert org_update_or_create.call_count == 2
    assert user_update_or_create.call_count == len(USERS)


@patch(
    "support.management.commands.seed_local_testdata.settings.COGNITO_ENDPOINT_URL",
    new="https://cognito-idp.eu-central-1.amazonaws.com",
)
def test_seed_local_testdata_rejects_aws_non_local_endpoint():
    with pytest.raises(CommandError):
        call_command("seed_local_testdata", verbosity=0)


@patch(
    "support.management.commands.seed_local_testdata.settings.COGNITO_ENDPOINT_URL",
    new="https://example.com/cognito",
)
def test_seed_local_testdata_rejects_custom_non_local_endpoint():
    with pytest.raises(CommandError):
        call_command("seed_local_testdata", verbosity=0)


@patch("support.management.commands.seed_local_testdata.CognitoClient")
@patch("support.management.commands.seed_local_testdata.HumanUser")
@patch("support.management.commands.seed_local_testdata.Organization")
def test_seed_local_testdata_fails_on_sub_mismatch(
    mock_organization,
    mock_human_user,
    mock_cognito_client,
):
    org_records = {
        "ch.bafu": SimpleNamespace(organization_id="ch.bafu"),
        "ch.swisstopo": SimpleNamespace(organization_id="ch.swisstopo"),
    }

    mock_organization.objects.update_or_create = MagicMock(
        side_effect=[
            (org_records["ch.bafu"], True),
            (org_records["ch.swisstopo"], True),
        ]
    )
    mock_human_user.objects.update_or_create = MagicMock()

    fake_cognito = MagicMock()
    fake_cognito.user_pool_id = "local"
    fake_cognito.client.admin_get_user.return_value = {
        "UserAttributes": [{"Name": "sub", "Value": "not-readable-sub"}]
    }
    mock_cognito_client.return_value = fake_cognito

    with pytest.raises(CommandError, match="expected 'superuser'"):
        call_command("seed_local_testdata", verbosity=0)


@patch("support.management.commands.seed_local_testdata.CognitoClient")
@patch("support.management.commands.seed_local_testdata.HumanUser")
@patch("support.management.commands.seed_local_testdata.Organization")
def test_seed_local_testdata_sets_sub_on_create(
    mock_organization,
    mock_human_user,
    mock_cognito_client,
):
    org_records = {
        "ch.bafu": SimpleNamespace(organization_id="ch.bafu"),
        "ch.swisstopo": SimpleNamespace(organization_id="ch.swisstopo"),
    }

    mock_organization.objects.update_or_create = MagicMock(
        side_effect=[
            (org_records["ch.bafu"], True),
            (org_records["ch.swisstopo"], True),
        ]
    )
    mock_human_user.objects.update_or_create = MagicMock(side_effect=_user_update_side_effect())

    fake_cognito = MagicMock()
    fake_cognito.user_pool_id = "local"
    fake_cognito.client.exceptions.UserNotFoundException = RuntimeError

    admin_get_user_side_effect: list[dict[str, list[dict[str, str]]] | RuntimeError] = []
    for sub in _seed_subs():
        admin_get_user_side_effect.extend(
            [
                RuntimeError(),
                {"UserAttributes": [{"Name": "sub", "Value": sub}]},
            ]
        )

    fake_cognito.client.admin_get_user.side_effect = admin_get_user_side_effect
    mock_cognito_client.return_value = fake_cognito

    call_command("seed_local_testdata", verbosity=0)

    created_subs = [
        call.kwargs["UserAttributes"][0]["Value"]
        for call in fake_cognito.client.admin_create_user.call_args_list
    ]
    assert created_subs == _seed_subs()
