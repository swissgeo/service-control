from unittest.mock import call, patch

from boto3 import client as real_client

from django.conf import settings

from cognito.utils.client import Client, CreateClientResponse, OrganizationGroup, UnitGroup


@patch("cognito.utils.client.client")
def test_create_user_group_organization(mock_boto3):
    client = Client()
    response = client.create_group(OrganizationGroup("test_org_id"))
    assert response is True
    assert (
        call().create_group(
            GroupName="O_test_org_id",
            UserPoolId=client.user_pool_id,
            Description="Managed by service-control",
        )
        in mock_boto3.mock_calls
    )


@patch("cognito.utils.client.client")
def test_create_user_group_unit(mock_boto3):
    client = Client()
    response = client.create_group(UnitGroup("test_unit_id", "test_org_id"))
    assert response is True
    assert (
        call().create_group(
            GroupName="U_test_org_id_test_unit_id",
            UserPoolId=client.user_pool_id,
            Description="Managed by service-control",
        )
        in mock_boto3.mock_calls
    )


@patch("cognito.utils.client.client")
def test_create_user_group_already_exists(mock_boto3):
    # Create a real boto3 client only to get the exception class
    group_exists_exception = real_client("cognito-idp").exceptions.GroupExistsException
    # Inject *real* exception class into the mock
    mock_boto3.return_value.exceptions.GroupExistsException = group_exists_exception
    mock_boto3.return_value.create_group.side_effect = group_exists_exception(
        error_response={},
        operation_name="",
    )

    client = Client()
    response = client.create_group(OrganizationGroup("group already exists"))
    assert response is False
    assert (
        call().create_group(
            GroupName="O_group already exists",
            UserPoolId=client.user_pool_id,
            Description="Managed by service-control",
        )
        in mock_boto3.mock_calls
    )


@patch("cognito.utils.client.client")
def test_delete_user_group(mock_boto3):
    client = Client()
    response = client.delete_group(name="test group name")
    assert response is True
    assert (
        call().delete_group(
            GroupName="test group name",
            UserPoolId=client.user_pool_id,
        )
        in mock_boto3.mock_calls
    )


@patch("cognito.utils.client.client")
def test_delete_user_group_not_found(mock_boto3):
    # Create a real boto3 client only to get the exception class
    group_exists_exception = real_client("cognito-idp").exceptions.ResourceNotFoundException
    # Inject *real* exception class into the mock
    mock_boto3.return_value.exceptions.ResourceNotFoundException = group_exists_exception
    mock_boto3.return_value.delete_group.side_effect = group_exists_exception(
        error_response={},
        operation_name="",
    )

    client = Client()
    response = client.delete_group(name="group not found")
    assert response is False
    assert (
        call().delete_group(
            GroupName="group not found",
            UserPoolId=client.user_pool_id,
        )
        in mock_boto3.mock_calls
    )


@patch("cognito.utils.client.client")
def test_create_app_client(mock_boto3):
    mock_boto3.return_value.create_user_pool_client.return_value = {
        "UserPoolClient": {
            "ClientName": "client_name",
            "ClientId": "client_id",
            "ClientSecret": "client_secret",
        }
    }
    client = Client()
    response = client.create_app_client(name="client_name", token_duration_mins=60)
    assert response == CreateClientResponse(
        name="client_name",
        client_id="client_id",
        client_secret="client_secret",
    )
    assert (
        call().create_user_pool_client(
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


@patch("cognito.utils.client.client")
def test_delete_app_client(mock_boto3):
    client = Client()
    response = client.delete_app_client(client_id="client_id")
    assert response is True
    assert (
        call().delete_user_pool_client(
            ClientId="client_id",
            UserPoolId=client.user_pool_id,
        )
        in mock_boto3.mock_calls
    )


@patch("cognito.utils.client.client")
def test_delete_app_client_not_found(mock_boto3):
    # Create a real boto3 client only to get the exception class
    client_exists_exception = real_client("cognito-idp").exceptions.ResourceNotFoundException
    # Inject *real* exception class into the mock
    mock_boto3.return_value.exceptions.ResourceNotFoundException = client_exists_exception
    mock_boto3.return_value.delete_user_pool_client.side_effect = client_exists_exception(
        error_response={},
        operation_name="",
    )

    client = Client()
    response = client.delete_app_client(client_id="client_id")
    assert response is False
    assert (
        call().delete_user_pool_client(
            ClientId="client_id",
            UserPoolId=client.user_pool_id,
        )
        in mock_boto3.mock_calls
    )


@patch("cognito.utils.client.client")
def test_update_user_roles_empty(mock_boto3):
    client = Client()
    client.update_user_roles(username="client_id", roles=[])
    assert (
        call().admin_update_user_attributes(
            UserPoolId=client.user_pool_id,
            Username="client_id",
            UserAttributes=[{"Name": "custom:roles", "Value": ""}],
        )
        in mock_boto3.mock_calls
    )


@patch("cognito.utils.client.client")
def test_update_user_roles_single(mock_boto3):
    client = Client()
    client.update_user_roles(username="client_id", roles=["first_role"])
    assert (
        call().admin_update_user_attributes(
            UserPoolId=client.user_pool_id,
            Username="client_id",
            UserAttributes=[{"Name": "custom:roles", "Value": "first_role"}],
        )
        in mock_boto3.mock_calls
    )


@patch("cognito.utils.client.client")
def test_update_user_roles_multiple(mock_boto3):
    client = Client()
    client.update_user_roles(username="client_id", roles=["first_role", "second_role"])
    assert (
        call().admin_update_user_attributes(
            UserPoolId=client.user_pool_id,
            Username="client_id",
            UserAttributes=[{"Name": "custom:roles", "Value": "first_role,second_role"}],
        )
        in mock_boto3.mock_calls
    )
