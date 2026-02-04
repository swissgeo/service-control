from functools import lru_cache
from typing import TYPE_CHECKING

from aiobotocore.session import AioSession, get_session
from pydantic import BaseModel

from django.conf import settings

if TYPE_CHECKING:
    from mypy_boto3_cognito_idp.type_defs import AttributeTypeTypeDef, ListUsersResponseTypeDef


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


@lru_cache(maxsize=1)
def get_session_cached() -> AioSession:
    return get_session()


class Client:
    """A low level client for managing cognito users and groups."""

    def __init__(self) -> None:
        self.endpoint_url = settings.COGNITO_ENDPOINT_URL
        self.user_pool_id = settings.COGNITO_POOL_ID
        self.session = get_session_cached()

    async def create_group(self, name: str) -> bool:
        """Create a new cognito user group.

        Returns False if the group already exists.
        """
        async with self.session.create_client(
            "cognito-idp", endpoint_url=self.endpoint_url
        ) as client:
            try:
                await client.create_group(
                    GroupName=name,
                    UserPoolId=self.user_pool_id,
                    Description="Managed by service-control",
                )
            except client.exceptions.GroupExistsException:
                return False

        return True

    async def delete_group(self, name: str) -> bool:
        """Delete the cognito user group.

        Returns False id the group does not exist.
        """
        async with self.session.create_client(
            "cognito-idp", endpoint_url=self.endpoint_url
        ) as client:
            try:
                await client.delete_group(GroupName=name, UserPoolId=self.user_pool_id)
            except client.exceptions.ResourceNotFoundException:
                return False
            return True

    async def create_app_client(
        self, name: str, token_duration_mins: int | None
    ) -> CreateClientResponse:
        """Create cognito app client"""
        if not token_duration_mins:
            token_duration_mins = int(settings.DEFAULT_M2M_TOKEN_DURATION_MINS)
        async with self.session.create_client(
            "cognito-idp", endpoint_url=self.endpoint_url
        ) as client:
            resp = await client.create_user_pool_client(
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

    async def delete_app_client(self, client_id: str) -> bool:
        """Delete cognito app client"""
        async with self.session.create_client(
            "cognito-idp", endpoint_url=self.endpoint_url
        ) as client:
            try:
                await client.delete_user_pool_client(
                    UserPoolId=self.user_pool_id,
                    ClientId=client_id,
                )
            except client.exceptions.ResourceNotFoundException:
                return False
            return True

    async def list_users(self, pagination_token: str | None) -> ListUsersResponseTypeDef:
        """List all users in user pool"""
        async with self.session.create_client(
            "cognito-idp", endpoint_url=self.endpoint_url
        ) as client:
            if pagination_token is not None:
                # Setting PaginationToken to None is not accepted
                return await client.list_users(
                    UserPoolId=self.user_pool_id, PaginationToken=pagination_token
                )
            return await client.list_users(UserPoolId=self.user_pool_id)

    def get_user_attribute(self, attrs: list[AttributeTypeTypeDef], name: str) -> str | None:
        """Get a user attribute value from a list of attributes"""
        for attr in attrs:
            if attr["Name"] == name:
                return attr["Value"]
        return None

    async def get_users(self, username: str) -> CognitoUser:
        """Get details of a user in user pool"""
        async with self.session.create_client(
            "cognito-idp", endpoint_url=self.endpoint_url
        ) as client:
            resp = await client.admin_get_user(UserPoolId=self.user_pool_id, Username=username)

        first_name = self.get_user_attribute(resp["UserAttributes"], "given_name")
        last_name = self.get_user_attribute(resp["UserAttributes"], "family_name")
        email = self.get_user_attribute(resp["UserAttributes"], "email")
        if not first_name or not last_name or not email:
            # These attributes are set as required in the user pool, so should always be present.
            # If not, raise an error to avoid creating incomplete user records in the database.
            raise Exception(f"User {username} is missing required attributes")  # noqa: TRY002, TRY003

        return CognitoUser(
            username=resp["Username"],
            first_name=first_name,
            last_name=last_name,
            email=email,
            org_name=self.get_user_attribute(resp["UserAttributes"], "custom:org_name"),
            org_name_abbr=self.get_user_attribute(resp["UserAttributes"], "custom:org_name_abbr"),
            org_unit_name=self.get_user_attribute(resp["UserAttributes"], "custom:org_unit_name"),
            org_uid=self.get_user_attribute(resp["UserAttributes"], "custom:org_uid"),
        )
