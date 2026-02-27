from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import User

from user.models import CustomUser, Role


@patch("user.signals.Client")
def test_custom_user_role_changes_sync_to_cognito(client_cls, organization):
    auth_user = User.objects.create(username=f"user-{uuid4().hex}")
    custom_user = CustomUser.objects.create(user=auth_user, organization=organization)

    role = Role.objects.create(
        role_id=f"role-{uuid4().hex}",
        name=f"Role {uuid4().hex}",
        description="",
    )

    custom_user.roles.add(role)
    assert client_cls.return_value.update_user_roles.call_args_list[-1].args == (
        auth_user.username,
        [role.role_id],
    )

    custom_user.roles.clear()
    assert client_cls.return_value.update_user_roles.call_args_list[-1].args == (
        auth_user.username,
        [],
    )
