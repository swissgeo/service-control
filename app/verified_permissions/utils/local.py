from verified_permissions.utils.base import BaseClient


class Client(BaseClient):
    """A dummy client to use during local development."""

    def __init__(self) -> None:
        pass

    def create_org_admin_policy(self, organization_id: str) -> str:  # noqa: ARG002 ..
        return "dummy-org-admin-policy-id"

    def create_dataset_admin_policy(self, unit_id: str) -> str:  # noqa: ARG002 ..
        return "dummy-dataset-admin-policy-id"

    def create_dataset_contributor_policy(self, unit_id: str) -> str:  # noqa: ARG002 ..
        return "dummy-dataset-contributor-policy-id"

    def delete_policy(self, policy_id: str) -> None:
        pass
