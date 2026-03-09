from unittest.mock import patch

from verified_permissions.utils.verified_permissions import Client


@patch("verified_permissions.utils.verified_permissions.client")
def test_create_org_admin_policy(mock_boto3, settings):
    # Setup
    settings.VERIFIED_PERMISSIONS_STORE_ID = "test-policy-store-id"
    settings.VERIFIED_PERMISSIONS_NAMESPACE = "test-namespace"
    settings.ROLE_POLICY_TEMPLATE_IDS = {
        settings.ORG_ADMIN: "test-org-admin-template-id",
        settings.DATASET_ADMIN: "test-dataset-admin-template-id",
        settings.DATASET_CONTRIBUTOR: "test-dataset-contributor-template-id",
    }
    settings.COGNITO_POOL_ID = "test-user-pool-id"
    mock_boto3.return_value.create_policy.return_value = {"policyId": "test-policy-id"}

    # Run
    client = Client()
    created_policy_id = client.create_org_admin_policy(organization_id="test-organization-id")

    # Assert
    assert created_policy_id == "test-policy-id"
    assert mock_boto3.return_value.create_policy.call_count == 1
    assert (
        mock_boto3.return_value.create_policy.call_args.kwargs["policyStoreId"]
        == "test-policy-store-id"
    )
    assert mock_boto3.return_value.create_policy.call_args.kwargs["definition"] == {
        "templateLinked": {
            "policyTemplateId": "test-org-admin-template-id",
            "principal": {
                "entityType": "test-namespace::UserGroup",
                "entityId": "test-user-pool-id|test-organization-id",
            },
            "resource": {
                "entityType": "test-namespace::Organization",
                "entityId": "test-organization-id",
            },
        }
    }


@patch("verified_permissions.utils.verified_permissions.client")
def test_create_dataset_admin_policy(mock_boto3, settings):
    # Setup
    settings.VERIFIED_PERMISSIONS_STORE_ID = "test-policy-store-id"
    settings.VERIFIED_PERMISSIONS_NAMESPACE = "test-namespace"
    settings.ROLE_POLICY_TEMPLATE_IDS = {
        settings.ORG_ADMIN: "test-org-admin-template-id",
        settings.DATASET_ADMIN: "test-dataset-admin-template-id",
        settings.DATASET_CONTRIBUTOR: "test-dataset-contributor-template-id",
    }
    settings.COGNITO_POOL_ID = "test-user-pool-id"
    mock_boto3.return_value.create_policy.return_value = {"policyId": "test-policy-id"}

    # Run
    client = Client()
    created_policy_id = client.create_dataset_admin_policy(unit_id="test-unit-id")

    # Assert
    assert created_policy_id == "test-policy-id"
    assert mock_boto3.return_value.create_policy.call_count == 1
    assert (
        mock_boto3.return_value.create_policy.call_args.kwargs["policyStoreId"]
        == "test-policy-store-id"
    )
    assert mock_boto3.return_value.create_policy.call_args.kwargs["definition"] == {
        "templateLinked": {
            "policyTemplateId": "test-dataset-admin-template-id",
            "principal": {
                "entityType": "test-namespace::UserGroup",
                "entityId": "test-user-pool-id|test-unit-id",
            },
            "resource": {
                "entityType": "test-namespace::Unit",
                "entityId": "test-unit-id",
            },
        }
    }


@patch("verified_permissions.utils.verified_permissions.client")
def test_create_dataset_contributor_policy(mock_boto3, settings):
    # Setup
    settings.VERIFIED_PERMISSIONS_STORE_ID = "test-policy-store-id"
    settings.VERIFIED_PERMISSIONS_NAMESPACE = "test-namespace"
    settings.ROLE_POLICY_TEMPLATE_IDS = {
        settings.ORG_ADMIN: "test-org-admin-template-id",
        settings.DATASET_ADMIN: "test-dataset-admin-template-id",
        settings.DATASET_CONTRIBUTOR: "test-dataset-contributor-template-id",
    }
    settings.COGNITO_POOL_ID = "test-user-pool-id"
    mock_boto3.return_value.create_policy.return_value = {"policyId": "test-policy-id"}

    # Run
    client = Client()
    created_policy_id = client.create_dataset_contributor_policy(unit_id="test-unit-id")

    # Assert
    assert created_policy_id == "test-policy-id"
    assert mock_boto3.return_value.create_policy.call_count == 1
    assert (
        mock_boto3.return_value.create_policy.call_args.kwargs["policyStoreId"]
        == "test-policy-store-id"
    )
    assert mock_boto3.return_value.create_policy.call_args.kwargs["definition"] == {
        "templateLinked": {
            "policyTemplateId": "test-dataset-contributor-template-id",
            "principal": {
                "entityType": "test-namespace::UserGroup",
                "entityId": "test-user-pool-id|test-unit-id",
            },
            "resource": {
                "entityType": "test-namespace::Unit",
                "entityId": "test-unit-id",
            },
        }
    }


@patch("verified_permissions.utils.verified_permissions.client")
def test_create_machine_user_policy(mock_boto3, settings):
    # Setup
    settings.VERIFIED_PERMISSIONS_STORE_ID = "test-policy-store-id"
    settings.VERIFIED_PERMISSIONS_NAMESPACE = "test-namespace"
    settings.ROLE_POLICY_TEMPLATE_IDS = {
        settings.ORG_ADMIN: "test-org-admin-template-id",
        settings.DATASET_ADMIN: "test-dataset-admin-template-id",
        settings.DATASET_CONTRIBUTOR: "test-dataset-contributor-template-id",
    }
    settings.COGNITO_POOL_ID = "test-user-pool-id"
    mock_boto3.return_value.create_policy.return_value = {"policyId": "test-policy-id"}

    # Run
    client = Client()
    created_policy_id = client.create_machine_user_policy(
        client_id="test-client-id", organization_id="test-organization-id"
    )

    # Assert
    assert created_policy_id == "test-policy-id"
    assert mock_boto3.return_value.create_policy.call_count == 1
    assert (
        mock_boto3.return_value.create_policy.call_args.kwargs["policyStoreId"]
        == "test-policy-store-id"
    )
    assert mock_boto3.return_value.create_policy.call_args.kwargs["definition"] == {
        "static": {
            "description": "Machine user policy",
            "statement": """permit (
    principal == test-namespace::User::"test-user-pool-id|test-client-id",
    action in test-namespace::Action::"org_admin_actions",
    resource == test-namespace::Organization::"test-organization-id"
);""",
        }
    }


@patch("verified_permissions.utils.verified_permissions.client")
def test_delete_policy(mock_boto3, settings):
    # Setup
    settings.VERIFIED_PERMISSIONS_STORE_ID = "test-policy-store-id"

    # Run
    client = Client()
    client.delete_policy(policy_id="test-policy-id")

    # Assert
    assert mock_boto3.return_value.delete_policy.call_count == 1
    assert (
        mock_boto3.return_value.delete_policy.call_args.kwargs["policyStoreId"]
        == "test-policy-store-id"
    )
    assert mock_boto3.return_value.delete_policy.call_args.kwargs["policyId"] == "test-policy-id"
