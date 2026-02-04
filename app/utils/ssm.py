from typing import TYPE_CHECKING

from aiobotocore.session import get_session

from django.conf import settings

if TYPE_CHECKING:
    from mypy_boto3_ssm.type_defs import GetParameterResultTypeDef


class SSMClient:
    """AWS client to manage ssm parameters"""

    def __init__(self) -> None:
        self.session = get_session()

    async def get_parameter(self, name: str) -> str:
        """Get SSM parameter value"""
        async with self.session.create_client("ssm") as client:
            resp: GetParameterResultTypeDef = await client.get_parameter(Name=name)
            return resp["Parameter"]["Value"]

    async def put_parameter(self, name: str, value: str) -> None:
        """Update SSM parameter value"""
        async with self.session.create_client("ssm") as client:
            await client.put_parameter(Name=name, Value=value, Overwrite=True)


class LocalClient:
    """Local parameter store client"""

    def __init__(self) -> None:
        pass

    async def get_parameter(
        self,
        name: str,  # noqa: ARG002 ..
    ) -> str:
        """Get SSM parameter value"""
        return "local,list,of,values"

    async def put_parameter(
        self,
        name: str,
        value: str,
    ) -> None:
        """Update SSM parameter value"""


Client = LocalClient if settings.USE_LOCAL_SSM_STORE else SSMClient
