from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import override_settings

from config.authorization import VPRole
from user.models import CustomUser, Role


@patch("user.models.Client")
def test_custom_user_stores_role_ids_as_list(cognito_client, organization):
    auth_user = User.objects.create(username="user1")
    custom_user = CustomUser.objects.create(
        user=auth_user,
        organization=organization,
        user_type=CustomUser.UserType.HUMAN,
        roles=[VPRole.ORG_ADMIN, VPRole.DATASET_CONTRIBUTOR],
    )

    assert custom_user.roles == [VPRole.ORG_ADMIN, VPRole.DATASET_CONTRIBUTOR]
    assert cognito_client.return_value.update_user_roles.called


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
