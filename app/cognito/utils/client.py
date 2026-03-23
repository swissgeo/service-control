from abc import ABC, abstractmethod

from boto3 import client
from pydantic import BaseModel

from django.conf import settings

from config.aws import config


class CreateClientResponse(BaseModel):
    name: str
    client_id: str
    client_secret: str


class CognitoUser(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: str
    org_name: str | None
    org_name_abbr: str | None
    org_unit_name: str | None
    org_uid: str | None


class CognitoUserGroup(ABC):
    """
    Base class for Cognito user groups. The group name is derived from the resource with a
    prefix. This allows to easily identify the type of the group (e.g. organization or unit) and
    avoid name clashes.
    """

    # The identifier of the resource this group relates to, e.g. organization_id or unit_id.
    resource_id: str
    prefix: str

    def __init__(self, resource_id: str) -> None:
        self.resource_id = resource_id

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the cognito user group."""


class OrganizationGroup(CognitoUserGroup):
    """
    Cognito groups that relate to an organization have the prefix "O_".
    """

    prefix = "O_"

    @property
    def name(self) -> str:
        return f"{self.prefix}{self.resource_id}"


class UnitGroup(CognitoUserGroup):
    """
    Cognito groups that relate to a unit have the prefix "U_", as well as the organization_id as
    part of the identifier to avoid name clashes between units of different organizations.
    """

    prefix = "U_"
    organization_id: str

    def __init__(self, identifier: str, organization_id: str) -> None:
        super().__init__(identifier)
        self.organization_id = organization_id

    @property
    def name(self) -> str:
        return f"{self.prefix}{self.organization_id}_{self.resource_id}"


class Client:
    """A low level client for managing cognito users and groups."""

    def __init__(self) -> None:
        self.endpoint_url = settings.COGNITO_ENDPOINT_URL
        self.user_pool_id = settings.COGNITO_POOL_ID
        self.client = client("cognito-idp", endpoint_url=self.endpoint_url, config=config)

    def create_group(self, group: CognitoUserGroup) -> bool:
        """Create a new cognito user group.

        Returns False if the group already exists.
        """
        try:
            self.client.create_group(
                GroupName=group.name,
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

    def create_app_client(self, name: str, token_duration_mins: int | None) -> CreateClientResponse:
        """Create cognito app client"""
        if not token_duration_mins:
            token_duration_mins = int(settings.DEFAULT_M2M_TOKEN_DURATION_MINS)
        resp = self.client.create_user_pool_client(
            UserPoolId=self.user_pool_id,
            ClientName=name,
            GenerateSecret=True,
            AccessTokenValidity=token_duration_mins,
            TokenValidityUnits={"AccessToken": "minutes"},
            AllowedOAuthFlowsUserPoolClient=True,
            AllowedOAuthFlows=["client_credentials"],
            ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"],
            AllowedOAuthScopes=[settings.DEFAULT_M2M_SCOPE],
        )
        return CreateClientResponse(
            name=resp["UserPoolClient"]["ClientName"],
            client_id=resp["UserPoolClient"]["ClientId"],
            client_secret=resp["UserPoolClient"]["ClientSecret"],
        )

    def delete_app_client(self, client_id: str) -> bool:
        """Delete cognito app client"""
        try:
            self.client.delete_user_pool_client(
                UserPoolId=self.user_pool_id,
                ClientId=client_id,
            )
        except self.client.exceptions.ResourceNotFoundException:
            return False
        return True

    def update_user_roles(self, username: str, roles: list[str]) -> None:
        """Update the roles of a user in user pool"""
        self.client.admin_update_user_attributes(
            UserPoolId=self.user_pool_id,
            Username=username,
            UserAttributes=[{"Name": "custom:roles", "Value": ",".join(roles)}],
        )
