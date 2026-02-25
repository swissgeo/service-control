from typing import TYPE_CHECKING, Any

from boto3 import client

from django.conf import settings

if TYPE_CHECKING:
    from mypy_boto3_ssm import SSMClient
    from mypy_boto3_ssm.type_defs import GetParameterResultTypeDef


class SSMClient:
    """AWS client to manage ssm parameters"""

    def __init__(self) -> None:
        self.client = client("ssm")

    def get_parameter(self, name: str) -> str:
        """Get SSM parameter value"""
        resp: GetParameterResultTypeDef = self.client.get_parameter(Name=name)
        return resp["Parameter"]["Value"]

    def put_parameter(self, name: str, value: str) -> None:
        """Update SSM parameter value"""
        self.client.put_parameter(Name=name, Value=value, Overwrite=True)

    @property
    def exceptions(self) -> Any:
        return self.client.exceptions


class LocalClient:
    """Local parameter store client"""

    def __init__(self) -> None:
        pass

    def get_parameter(
        self,
        name: str,  # noqa: ARG002 ..
    ) -> str:
        """Get SSM parameter value"""
        return "local,list,of,values"

    def put_parameter(
        self,
        name: str,
        value: str,
    ) -> None:
        """Update SSM parameter value"""

    @property
    def exceptions(self) -> LocalClientExceptions:
        return LocalClientExceptions()


class LocalClientExceptions:
    """Local Client dummy exceptions

    This is needed because of real SSM client exception that we need to catch
    """

    ValidationException = ValueError


Client = LocalClient if settings.USE_LOCAL_SSM_STORE else SSMClient
