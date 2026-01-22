from unittest.mock import call
from unittest.mock import patch

from boto3 import client as real_client
from cognito.utils.client import Client


@patch('cognito.utils.client.client')
def test_create_user_group(mock_boto3):
    client = Client()
    response = client.create_group(name='test group name')
    assert response is True
    assert call().create_group(
        GroupName='test group name',
        UserPoolId=client.user_pool_id,
        Description='Managed by service-control',
    ) in mock_boto3.mock_calls


@patch('cognito.utils.client.client')
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
    response = client.create_group(name='group already exists')
    assert response is False
    assert call().create_group(
        GroupName='group already exists',
        UserPoolId=client.user_pool_id,
        Description='Managed by service-control',
    ) in mock_boto3.mock_calls


@patch('cognito.utils.client.client')
def test_delete_user_group(mock_boto3):
    client = Client()
    response = client.delete_group(name='test group name')
    assert response is True
    assert call().delete_group(
        GroupName='test group name',
        UserPoolId=client.user_pool_id,
    ) in mock_boto3.mock_calls


@patch('cognito.utils.client.client')
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
    response = client.delete_group(name='group not found')
    assert response is False
    assert call().delete_group(
        GroupName='group not found',
        UserPoolId=client.user_pool_id,
    ) in mock_boto3.mock_calls
