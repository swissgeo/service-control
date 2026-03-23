from unittest.mock import patch

from django.http import HttpRequest

from cognito.utils.client import OrganizationGroup, UnitGroup
from config.authorization import VPRole
from utils import api_path
from verified_permissions.utils.verified_permissions import Client


@patch("verified_permissions.utils.verified_permissions._get_client")
def test_create_org_admin_policy(mock_boto3, settings):
    # Setup
    settings.VERIFIED_PERMISSIONS_STORE_ID = "test-policy-store-id"
    settings.VERIFIED_PERMISSIONS_NAMESPACE = "test-namespace"
    settings.ROLE_POLICY_TEMPLATE_IDS = {
        VPRole.ORG_ADMIN: "test-org-admin-template-id",
        VPRole.DATASET_ADMIN: "test-dataset-admin-template-id",
        VPRole.DATASET_CONTRIBUTOR: "test-dataset-contributor-template-id",
    }
    settings.COGNITO_POOL_ID = "test-user-pool-id"
    mock_boto3.return_value.create_policy.return_value = {"policyId": "test-policy-id"}

    # Run
    client = Client()
    created_policy_id = client.create_org_admin_policy(OrganizationGroup("test-organization-id"))

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
                "entityId": "test-user-pool-id|O_test-organization-id",
            },
            "resource": {
                "entityType": "test-namespace::Organization",
                "entityId": "test-organization-id",
            },
        }
    }


@patch("verified_permissions.utils.verified_permissions._get_client")
def test_create_dataset_admin_policy(mock_boto3, settings):
    # Setup
    settings.VERIFIED_PERMISSIONS_STORE_ID = "test-policy-store-id"
    settings.VERIFIED_PERMISSIONS_NAMESPACE = "test-namespace"
    settings.ROLE_POLICY_TEMPLATE_IDS = {
        VPRole.ORG_ADMIN: "test-org-admin-template-id",
        VPRole.DATASET_ADMIN: "test-dataset-admin-template-id",
        VPRole.DATASET_CONTRIBUTOR: "test-dataset-contributor-template-id",
    }
    settings.COGNITO_POOL_ID = "test-user-pool-id"
    mock_boto3.return_value.create_policy.return_value = {"policyId": "test-policy-id"}

    # Run
    client = Client()
    created_policy_id = client.create_dataset_admin_policy(
        UnitGroup("test-unit-id", "test-organization-id")
    )

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
                "entityId": "test-user-pool-id|U_test-organization-id_test-unit-id",
            },
            "resource": {
                "entityType": "test-namespace::Unit",
                "entityId": "test-unit-id",
            },
        }
    }


@patch("verified_permissions.utils.verified_permissions._get_client")
def test_create_dataset_contributor_policy(mock_boto3, settings):
    # Setup
    settings.VERIFIED_PERMISSIONS_STORE_ID = "test-policy-store-id"
    settings.VERIFIED_PERMISSIONS_NAMESPACE = "test-namespace"
    settings.ROLE_POLICY_TEMPLATE_IDS = {
        VPRole.ORG_ADMIN: "test-org-admin-template-id",
        VPRole.DATASET_ADMIN: "test-dataset-admin-template-id",
        VPRole.DATASET_CONTRIBUTOR: "test-dataset-contributor-template-id",
    }
    settings.COGNITO_POOL_ID = "test-user-pool-id"
    mock_boto3.return_value.create_policy.return_value = {"policyId": "test-policy-id"}

    # Run
    client = Client()
    created_policy_id = client.create_dataset_contributor_policy(
        UnitGroup("test-unit-id", "test-organization-id")
    )

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
                "entityId": "test-user-pool-id|U_test-organization-id_test-unit-id",
            },
            "resource": {
                "entityType": "test-namespace::Unit",
                "entityId": "test-unit-id",
            },
        }
    }


@patch("verified_permissions.utils.verified_permissions._get_client")
def test_create_machine_user_policy(mock_boto3, settings):
    # Setup
    settings.VERIFIED_PERMISSIONS_STORE_ID = "test-policy-store-id"
    settings.VERIFIED_PERMISSIONS_NAMESPACE = "test-namespace"
    settings.ROLE_POLICY_TEMPLATE_IDS = {
        VPRole.ORG_ADMIN: "test-org-admin-template-id",
        VPRole.DATASET_ADMIN: "test-dataset-admin-template-id",
        VPRole.DATASET_CONTRIBUTOR: "test-dataset-contributor-template-id",
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
    resource in test-namespace::Organization::"test-organization-id"
);""",
        }
    }


@patch("verified_permissions.utils.verified_permissions._get_client")
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


def test_build_entities_organization():
    # Setup
    client = Client()
    resource = api_path.Organization
    request = HttpRequest()
    request.resolver_match = type(
        "ResolverMatch", (), {"kwargs": {"organization_id": "org123", "unit_id": "unit123"}}
    )()

    # Run
    entities = client._build_entities(resource, request)  # noqa: SLF001

    # Assert
    assert entities == {
        "entityList": [
            {
                "identifier": {
                    "entityId": "org123",
                    "entityType": "swissgeo::Organization",
                },
                "parents": [],
            },
        ],
    }


def test_build_entities_with_parents():
    # Setup
    client = Client()
    resource = api_path.Unit
    request = HttpRequest()
    request.resolver_match = type(
        "ResolverMatch", (), {"kwargs": {"organization_id": "org123", "unit_id": "unit123"}}
    )()

    # Run
    entities = client._build_entities(resource, request)  # noqa: SLF001

    # Assert
    assert entities == {
        "entityList": [
            {
                "identifier": {
                    "entityId": "unit123",
                    "entityType": "swissgeo::Unit",
                },
                "parents": [
                    {
                        "entityId": "org123",
                        "entityType": "swissgeo::Organization",
                    },
                ],
            },
            {
                "identifier": {
                    "entityId": "org123",
                    "entityType": "swissgeo::Organization",
                },
                "parents": [],
            },
        ],
    }
