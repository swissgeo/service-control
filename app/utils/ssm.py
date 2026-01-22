from typing import TYPE_CHECKING

from boto3 import client
from django.conf import settings

if TYPE_CHECKING:
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
        self.client.put_parameter(Name=name, Value=value)


class LocalClient:
    """Local parameter store client"""

    def __init__(self) -> None:
        pass

    def get_parameter(self, name: str) -> str:
        """Get SSM parameter value"""
        _ = name
        return "local,list,of,values"

    def put_parameter(self, name: str, value: str) -> None:
        """Update SSM parameter value"""
        _, _ = name, value


Client = LocalClient if settings.USE_LOCAL_SSM_STORE else SSMClient
