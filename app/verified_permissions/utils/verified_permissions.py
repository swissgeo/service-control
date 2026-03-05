from boto3 import client

from django.conf import settings

from config.aws import config
from verified_permissions.utils.base import BaseClient


class Client(BaseClient):
    """A low level client for managing verified permissions policies."""

    def __init__(self) -> None:
        self.policy_store_id = settings.VERIFIED_PERMISSIONS_STORE_ID
        self.namespace = settings.VERIFIED_PERMISSIONS_NAMESPACE
        self.user_pool_id = settings.COGNITO_POOL_ID
        self.client = client("verifiedpermissions", config=config)

    def create_org_admin_policy(self, organization_id: str) -> str:
        """Create a policy an organization admin policy to manage their organization.

        Args:
            organization_id (str): The ID of the organization.

        Returns:
            str: The ID of the created policy.
        """
        resp = self.client.create_policy(
            # clientToken='string', # Optional: set for idempotency on retries
            policyStoreId=self.policy_store_id,
            definition={
                "templateLinked": {
                    "policyTemplateId": settings.ROLE_POLICY_TEMPLATE_IDS[settings.ORG_ADMIN],
                    "principal": {
                        "entityType": "swissgeo::UserGroup",
                        "entityId": f"{self.user_pool_id}|{organization_id}",
                    },
                    "resource": {
                        "entityType": "swissgeo::Organization",
                        "entityId": organization_id,
                    },
                }
            },
        )
        return resp["policyId"]

    def create_dataset_admin_policy(self, unit_id: str) -> str:
        """Create a dataset admin policy to manage datasets in a unit.

        Args:
            unit_id (str): The ID of the unit.

        Returns:
            str: The ID of the created policy.
        """
        resp = self.client.create_policy(
            # clientToken='string', # Optional: set for idempotency on retries
            policyStoreId=self.policy_store_id,
            definition={
                "templateLinked": {
                    "policyTemplateId": settings.ROLE_POLICY_TEMPLATE_IDS[settings.DATASET_ADMIN],
                    "principal": {
                        "entityType": "swissgeo::UserGroup",
                        "entityId": f"{self.user_pool_id}|{unit_id}",
                    },
                    "resource": {"entityType": "swissgeo::Unit", "entityId": unit_id},
                }
            },
        )
        return resp["policyId"]

    def create_dataset_contributor_policy(self, unit_id: str) -> str:
        """Create a dataset contributor policy to manage datasets in a unit.

        Args:
            unit_id (str): The ID of the unit.

        Returns:
            str: The ID of the created policy.
        """
        resp = self.client.create_policy(
            # clientToken='string', # Optional: set for idempotency on retries
            policyStoreId=self.policy_store_id,
            definition={
                "templateLinked": {
                    "policyTemplateId": settings.ROLE_POLICY_TEMPLATE_IDS[
                        settings.DATASET_CONTRIBUTOR
                    ],
                    "principal": {
                        "entityType": "swissgeo::UserGroup",
                        "entityId": f"{self.user_pool_id}|{unit_id}",
                    },
                    "resource": {"entityType": "swissgeo::Unit", "entityId": unit_id},
                }
            },
        )
        return resp["policyId"]

    def delete_policy(self, policy_id: str) -> None:
        """Remove a policy.

        Args:
            policy_id (str): The ID of the policy to be removed.
        """
        self.client.delete_policy(policyId=policy_id, policyStoreId=self.policy_store_id)
