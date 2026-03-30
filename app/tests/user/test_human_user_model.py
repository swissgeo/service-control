from unittest.mock import patch

from django.test import override_settings

import pytest

from cognito.utils.client import OrganizationGroup, UnitGroup
from config.authorization import VPRole
from organization.models import Organization, Unit
from user.models import CustomUser, HumanUser, Role


@patch("user.models.Client")
def test_human_user_stores_role_ids_as_list(cognito_client, organization):
    user = HumanUser.objects.create(
        sub="user1",
        cognito_username="prefix-user1",
        organization=organization,
    )

    # Roles are only store on update, not on create, so we need to call save here to store the
    # roles in cognito for the first time.
    user.roles = [VPRole.ORG_ADMIN, VPRole.DATASET_CONTRIBUTOR]
    user.save()

    assert user.roles == [VPRole.ORG_ADMIN, VPRole.DATASET_CONTRIBUTOR]
    assert cognito_client.return_value.update_user_roles.called
    assert cognito_client.return_value.update_user_roles.call_args[0][0] == "prefix-user1"
    assert set(cognito_client.return_value.update_user_roles.call_args[0][1]) == {
        VPRole.ORG_ADMIN,
        VPRole.DATASET_CONTRIBUTOR,
    }


@override_settings(
    ROLE_POLICY_TEMPLATE_IDS={
        VPRole.ORG_ADMIN: "some_id_for_org_admin",
        VPRole.DATASET_ADMIN: None,
        VPRole.DATASET_CONTRIBUTOR: "some_id_for_dataset_contributor",
    }
)
def test_role_catalog_loads_external_ids_from_settings():
    roles_by_id = {role.role_id: role for role in Role.all()}

    assert roles_by_id[VPRole.ORG_ADMIN.value].policy_template_id == "some_id_for_org_admin"
    assert roles_by_id[VPRole.DATASET_ADMIN.value].policy_template_id is None
    assert (
        roles_by_id[VPRole.DATASET_CONTRIBUTOR.value].policy_template_id
        == "some_id_for_dataset_contributor"
    )


def test_user_without_organization_or_unit_can_be_created(db):
    user = CustomUser.objects.create(
        sub="user1",
        cognito_username="prefix-user1",
        user_type=CustomUser.UserType.HUMAN,
    )
    assert user.organization is None
    assert user.unit is None


def test_user_unit_without_organization_fails(unit):
    with pytest.raises(ValueError, match="Unit must belong to the same organization as the user"):
        CustomUser.objects.create(
            sub="user1",
            cognito_username="prefix-user1",
            unit=unit,
            user_type=CustomUser.UserType.HUMAN,
        )


@patch("organization.models.VPClient")
@patch("organization.models.Client")
def test_user_unit_must_belong_to_same_organization(client, vp_client, organization, unit):
    vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id"
    vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
    vp_client.return_value.create_dataset_contributor_policy.return_value = (
        "mock-contributor-policy-id"
    )
    other_organization = Organization.objects.create(
        organization_id="other_id",
        acronym_de="Other",
        acronym_fr="Other",
        acronym_en="Other",
        name_de="Other",
        name_fr="Other",
        name_en="Other",
    )

    with pytest.raises(ValueError, match="Unit must belong to the same organization as the user"):
        CustomUser.objects.create(
            sub="user1",
            cognito_username="prefix-user1",
            organization=other_organization,
            unit=unit,
            user_type=CustomUser.UserType.HUMAN,
        )


@patch("organization.models.VPClient")
@patch("user.models.Client")
def test_user_organization_change(client, vp_client, organization, unit, user):
    vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id"
    vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
    vp_client.return_value.create_dataset_contributor_policy.return_value = (
        "mock-contributor-policy-id"
    )
    user.organization = Organization.objects.create(
        organization_id="other_id",
        acronym_de="Other",
        acronym_fr="Other",
        acronym_en="Other",
        name_de="Other",
        name_fr="Other",
        name_en="Other",
    )
    user.unit = None
    user.save()

    assert user.organization.organization_id == "other_id"
    calls = client.return_value.remove_user_from_group.call_args_list
    assert len(calls) == 2
    assert calls[0].args[0] == user.cognito_username
    assert calls[1].args[0] == user.cognito_username
    groups = [c.args[1] for c in client.return_value.remove_user_from_group.call_args_list]
    assert any(isinstance(g, UnitGroup) and g.resource_id == unit.unit_id for g in groups)
    assert any(
        isinstance(g, OrganizationGroup) and g.resource_id == organization.organization_id
        for g in groups
    )

    assert client.return_value.add_user_to_group.called
    assert client.return_value.add_user_to_group.call_args[0][0] == user.cognito_username
    group_arg = client.return_value.add_user_to_group.call_args[0][1]
    assert isinstance(group_arg, OrganizationGroup)
    assert group_arg.resource_id == "other_id"


@patch("organization.models.VPClient")
@patch("user.models.Client")
def test_user_unit_change(client, vp_client, unit, user):
    vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id"
    vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
    vp_client.return_value.create_dataset_contributor_policy.return_value = (
        "mock-contributor-policy-id"
    )

    user.unit = Unit.objects.create(
        unit_id="other_unit_id",
        organization=unit.organization,
        name_de="Other Unit",
        name_fr="Other Unit",
        name_en="Other Unit",
    )
    user.save()

    assert user.unit.unit_id == "other_unit_id"
    assert client.return_value.remove_user_from_group.called
    assert client.return_value.remove_user_from_group.call_args[0][0] == user.cognito_username
    group_arg = client.return_value.remove_user_from_group.call_args[0][1]
    assert isinstance(group_arg, UnitGroup)
    assert group_arg.resource_id == unit.unit_id
    assert client.return_value.add_user_to_group.called
    assert client.return_value.add_user_to_group.call_args[0][0] == user.cognito_username
    group_arg = client.return_value.add_user_to_group.call_args[0][1]
    assert isinstance(group_arg, UnitGroup)
    assert group_arg.resource_id == "other_unit_id"
