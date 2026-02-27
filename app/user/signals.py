import logging
from typing import TYPE_CHECKING, Any

from cognito.utils.client import Client

if TYPE_CHECKING:
    from user.models import CustomUser


logger = logging.getLogger(__name__)


def sync_custom_user_roles_to_cognito(
    sender: CustomUser,  # noqa: ARG001
    instance: CustomUser,
    **kwargs: dict[str, Any],  # noqa: ARG001
) -> None:
    """Synchronize role changes to Cognito whenever the roles M2M relation changes."""

    client = Client()
    client.update_user_roles(
        instance.user.username,
        [role.role_id for role in instance.roles.all()],
    )
