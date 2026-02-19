import logging
from typing import TYPE_CHECKING, Any, cast

from cognito.utils.client import Client

if TYPE_CHECKING:
    from organization.models import Organization, Unit

logger = logging.getLogger(__name__)


async def organization_post_save(sender: type, **kwargs: dict[str, Any]) -> None:  # noqa: ARG001
    if kwargs.get("created", False) and (instance := kwargs.get("instance")):
        instance = cast("Organization", instance)
        client = Client()
        if not await client.create_group(instance.organization_id):
            logger.warning(
                "cognito user group '%s' already exists, not created",
                instance.organization_id,
            )


async def organization_post_delete(sender: type, **kwargs: dict[str, Any]) -> None:  # noqa: ARG001
    if instance := kwargs.get("instance"):
        instance = cast("Organization", instance)
        client = Client()
        if not await client.delete_group(instance.organization_id):
            logger.warning(
                "cognito user group '%s' not found, not deleted", instance.organization_id
            )


async def unit_post_save(sender: type, **kwargs: dict[str, Any]) -> None:  # noqa: ARG001
    if kwargs.get("created", False) and (instance := kwargs.get("instance")):
        instance = cast("Unit", instance)
        client = Client()
        if not await client.create_group(instance.unit_id):
            logger.warning(
                "cognito user group '%s' already exists, not created",
                instance.unit_id,
            )


async def unit_post_delete(sender: type, **kwargs: dict[str, Any]) -> None:  # noqa: ARG001
    if instance := kwargs.get("instance"):
        instance = cast("Unit", instance)
        client = Client()
        if not await client.delete_group(instance.unit_id):
            logger.warning("cognito user group '%s' not found, not deleted", instance.unit_id)
