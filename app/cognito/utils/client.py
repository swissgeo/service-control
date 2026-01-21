from boto3 import client
from django.conf import settings


class Client:
    """A low level client for managing cognito users and groups."""

    def __init__(self) -> None:
        self.endpoint_url = settings.COGNITO_ENDPOINT_URL
        self.user_pool_id = settings.COGNITO_POOL_ID
        self.managed_flag_name = settings.COGNITO_MANAGED_FLAG_NAME
        self.client = client("cognito-idp", endpoint_url=self.endpoint_url)

    def create_group(self, name: str) -> bool:
        """Create a new cognito user group.

        Returns False if the group already exists.
        """
        try:
            self.client.create_group(
                GroupName=name,
                UserPoolId=self.user_pool_id,
                Description="Managed by service-control",
            )
        except self.client.exceptions.GroupExistsException:
            return False
        return True

    def delete_group(self, name: str) -> bool:
        """Delete the cognito user group.

        Returns False id the group does not exist.
        """
        try:
            self.client.delete_group(GroupName=name, UserPoolId=self.user_pool_id)
        except self.client.exceptions.ResourceNotFoundException:
            return False
        return True
