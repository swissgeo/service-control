import logging
from typing import TYPE_CHECKING, Any, cast

from cognito.utils.client import Client
from user.extra_audience import remove_extra_audience

if TYPE_CHECKING:
    from user.models import MachineUser

logger = logging.getLogger(__name__)


async def machine_user_post_delete(sender: type, **kwargs: dict[str, Any]) -> None:  # noqa: ARG001
    if instance := kwargs.get("instance"):
        instance = cast("MachineUser", instance)
        client = Client()
        if not await client.delete_app_client(instance.machine_user_id):
            logger.warning(
                "cognito app client '%s' not found, not deleted", instance.machine_user_id
            )
        await remove_extra_audience(instance.machine_user_id)
