from typing import Any
from unittest.mock import call, patch

from boto3 import client as real_client

from django.conf import settings

import pytest

from cognito.utils.client import Client, CreateClientResponse
from utils.testing import AsyncMagicMock


class CognitoMock(AsyncMagicMock):
    def create_client(self, *args: Any, **kwargs: Any) -> Any:  # noqa:ARG002
        # The original function (AioSession.create_client) is sync, not async.
        # We create and return a new AsyncMock which later can be inspected.
        return self.client


@pytest.mark.asyncio
@patch("cognito.utils.client.get_session_cached", new_callable=CognitoMock)
async def test_create_user_group(mock_boto3):
    client = Client()
    response = await client.create_group(name="test group name")
    assert response is True
    assert (
        call()
        .client.__aenter__()
        .create_group(
            GroupName="test group name",
            UserPoolId=client.user_pool_id,
            Description="Managed by service-control",
        )
        in mock_boto3.mock_calls
    )


@pytest.mark.asyncio
@patch("cognito.utils.client.get_session_cached", new_callable=CognitoMock)
async def test_create_user_group_already_exists(mock_boto3):
    # Create a real boto3 client only to get the exception class
    group_exists_exception = real_client("cognito-idp").exceptions.GroupExistsException
    # Inject *real* exception class into the mock
    mock_boto3.return_value.client.__aenter__.return_value.exceptions.GroupExistsException = (
        group_exists_exception
    )
    mock_boto3.return_value.client.__aenter__.return_value.create_group.side_effect = (
        group_exists_exception(
            error_response={},
            operation_name="",
        )
    )

    client = Client()
    response = await client.create_group(name="group already exists")
    assert response is False
    assert (
        call()
        .client.__aenter__()
        .create_group(
            GroupName="group already exists",
            UserPoolId=client.user_pool_id,
            Description="Managed by service-control",
        )
        in mock_boto3.mock_calls
    )


@pytest.mark.asyncio
@patch("cognito.utils.client.get_session_cached", new_callable=CognitoMock)
async def test_delete_user_group(mock_boto3):
    client = Client()
    response = await client.delete_group(name="test group name")
    assert response is True
    assert (
        call()
        .client.__aenter__()
        .delete_group(
            GroupName="test group name",
            UserPoolId=client.user_pool_id,
        )
        in mock_boto3.mock_calls
    )


@pytest.mark.asyncio
@patch("cognito.utils.client.get_session_cached", new_callable=CognitoMock)
async def test_delete_user_group_not_found(mock_boto3):
    # Create a real boto3 client only to get the exception class
    group_exists_exception = real_client("cognito-idp").exceptions.ResourceNotFoundException
    # Inject *real* exception class into the mock
    mock_boto3.return_value.client.__aenter__.return_value.exceptions.ResourceNotFoundException = (
        group_exists_exception
    )
    mock_boto3.return_value.client.__aenter__.return_value.delete_group.side_effect = (
        group_exists_exception(
            error_response={},
            operation_name="",
        )
    )

    client = Client()
    response = await client.delete_group(name="group not found")
    assert response is False
    assert (
        call()
        .client.__aenter__()
        .delete_group(
            GroupName="group not found",
            UserPoolId=client.user_pool_id,
        )
        in mock_boto3.mock_calls
    )


@pytest.mark.asyncio
@patch("cognito.utils.client.get_session_cached", new_callable=CognitoMock)
async def test_create_app_client(mock_boto3):
    mock_boto3.return_value.client.__aenter__.return_value.create_user_pool_client.return_value = {
        "UserPoolClient": {
            "ClientName": "client_name",
            "ClientId": "client_id",
            "ClientSecret": "client_secret",
        }
    }
    client = Client()
    response = await client.create_app_client(name="client_name", token_duration_mins=60)
    assert response == CreateClientResponse(
        name="client_name",
        client_id="client_id",
        client_secret="client_secret",  # noqa:S106
    )
    assert (
        call()
        .client.__aenter__()
        .create_user_pool_client(
            UserPoolId=client.user_pool_id,
            ClientName="client_name",
            GenerateSecret=True,
            AccessTokenValidity=60,
            TokenValidityUnits={"AccessToken": "minutes"},
            AllowedOAuthFlowsUserPoolClient=True,
            AllowedOAuthFlows=["client_credentials"],
            ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"],
            AllowedOAuthScopes=[settings.DEFAULT_M2M_SCOPE],
        )
        in mock_boto3.mock_calls
    )


@pytest.mark.asyncio
@patch("cognito.utils.client.get_session_cached", new_callable=CognitoMock)
async def test_delete_app_client(mock_boto3):
    client = Client()
    response = await client.delete_app_client(client_id="client_id")
    assert response is True
    assert (
        call()
        .client.__aenter__()
        .delete_user_pool_client(
            ClientId="client_id",
            UserPoolId=client.user_pool_id,
        )
        in mock_boto3.mock_calls
    )


@pytest.mark.asyncio
@patch("cognito.utils.client.get_session_cached", new_callable=CognitoMock)
async def test_delete_app_client_not_found(mock_boto3):
    # Create a real boto3 client only to get the exception class
    client_exists_exception = real_client("cognito-idp").exceptions.ResourceNotFoundException
    # Inject *real* exception class into the mock
    mock_boto3.return_value.client.__aenter__.return_value.exceptions.ResourceNotFoundException = (
        client_exists_exception
    )
    mock_boto3.return_value.client.__aenter__.return_value.delete_user_pool_client.side_effect = (
        client_exists_exception(
            error_response={},
            operation_name="",
        )
    )

    client = Client()
    response = await client.delete_app_client(client_id="client_id")
    assert response is False
    assert (
        call()
        .client.__aenter__()
        .delete_user_pool_client(
            ClientId="client_id",
            UserPoolId=client.user_pool_id,
        )
        in mock_boto3.mock_calls
    )


@pytest.mark.asyncio
@patch("cognito.utils.client.get_session_cached", new_callable=CognitoMock)
async def test_list_users(mock_boto3):
    client = Client()
    await client.list_users(pagination_token=None)
    assert (
        call()
        .client.__aenter__()
        .list_users(
            UserPoolId=client.user_pool_id,
        )
        in mock_boto3.mock_calls
    )


@pytest.mark.asyncio
@patch("cognito.utils.client.get_session_cached", new_callable=CognitoMock)
async def test_list_users_paginated(mock_boto3):
    client = Client()
    await client.list_users(pagination_token="token")  # noqa: S106
    assert (
        call()
        .client.__aenter__()
        .list_users(UserPoolId=client.user_pool_id, PaginationToken="token")
        in mock_boto3.mock_calls
    )


# TODO: add test for get_user_attribute
# TODO: add test for get_users (should probably be called get_user)
