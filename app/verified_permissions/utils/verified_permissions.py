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
        return self._create_policy_from_template(
            settings.ROLE_POLICY_TEMPLATE_IDS[settings.ORG_ADMIN],
            {
                "entityType": f"{self.namespace}::UserGroup",
                "entityId": f"{self.user_pool_id}|{organization_id}",
            },
            {
                "entityType": f"{self.namespace}::Organization",
                "entityId": organization_id,
            },
        )

    def create_dataset_admin_policy(self, unit_id: str) -> str:
        """Create a dataset admin policy to manage datasets in a unit.

        Args:
            unit_id (str): The ID of the unit.

        Returns:
            str: The ID of the created policy.
        """
        return self._create_policy_from_template(
            settings.ROLE_POLICY_TEMPLATE_IDS[settings.DATASET_ADMIN],
            {
                "entityType": f"{self.namespace}::UserGroup",
                "entityId": f"{self.user_pool_id}|{unit_id}",
            },
            {
                "entityType": f"{self.namespace}::Unit",
                "entityId": unit_id,
            },
        )

    def create_dataset_contributor_policy(self, unit_id: str) -> str:
        """Create a dataset contributor policy to manage datasets in a unit.

        Args:
            unit_id (str): The ID of the unit.

        Returns:
            str: The ID of the created policy.
        """
        return self._create_policy_from_template(
            settings.ROLE_POLICY_TEMPLATE_IDS[settings.DATASET_CONTRIBUTOR],
            {
                "entityType": f"{self.namespace}::UserGroup",
                "entityId": f"{self.user_pool_id}|{unit_id}",
            },
            {
                "entityType": f"{self.namespace}::Unit",
                "entityId": unit_id,
            },
        )

    def delete_policy(self, policy_id: str) -> None:
        """Remove a policy.

        Args:
            policy_id (str): The ID of the policy to be removed.
        """
        self.client.delete_policy(policyId=policy_id, policyStoreId=self.policy_store_id)

    def create_machine_user_policy(self, client_id: str, organization_id: str) -> str:
        """Create policy to authorize machine users based on their client_id
        TODO: For now machine users are org admins. This must change once we properly define the
        permissions of machine users.

        Args:
            client_id (str): The ID of the machine user client.
            organization_id (str): The ID of the organization.

        Returns:
            str: The ID of the created policy.
        """
        resp = self.client.create_policy(
            # clientToken='string', # Optional: set for idempotency on retries
            policyStoreId=self.policy_store_id,
            definition={
                "static": {
                    "description": "Machine user policy",
                    "statement": f"""permit (
    principal == {self.namespace}::User::"{self.user_pool_id}|{client_id}",
    action in {self.namespace}::Action::"org_admin_actions",
    resource == {self.namespace}::Organization::"{organization_id}"
);""",
                }
            },
        )
        return resp["policyId"]

    def _create_policy_from_template(
        self, template_id: str, principal: dict, resource: dict
    ) -> str:
        resp = self.client.create_policy(
            # clientToken='string', # Optional: set for idempotency on retries
            policyStoreId=self.policy_store_id,
            definition={
                "templateLinked": {
                    "policyTemplateId": template_id,
                    "principal": principal,
                    "resource": resource,
                }
            },
        )
        return resp["policyId"]
