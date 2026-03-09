from abc import ABC, abstractmethod


class VerifiedPermissionsResource:
    """Mixin for Django models that can be used as a resource in a Verified Permissions request.

    Subclasses must declare a "vp_entity_type" class attribute (the Verified Permissions entity type
    name without the namespace prefix, e.g. "Organization") and implement
    "get_vp_entity_id".  Override "get_vp_parents" when the entity has parent entities.
    """

    vp_entity_type: str

    def get_vp_entity_id(self) -> str:
        """Return the bare entity ID (no namespace prefix)."""
        raise NotImplementedError

    def get_vp_parents(self) -> list[VerifiedPermissionsResource]:
        """Return parent resources for this entity (default: none)."""
        return []


class BaseClient(ABC):
    @abstractmethod
    def create_org_admin_policy(self, organization_id: str) -> str: ...

    @abstractmethod
    def create_dataset_admin_policy(self, unit_id: str) -> str: ...

    @abstractmethod
    def create_dataset_contributor_policy(self, unit_id: str) -> str: ...

    @abstractmethod
    def delete_policy(self, policy_id: str) -> None: ...

    @abstractmethod
    def create_machine_user_policy(self, client_id: str, organization_id: str) -> str: ...

    @abstractmethod
    def is_authorized(
        self,
        token: str,
        action: str,
        resource: VerifiedPermissionsResource,
    ) -> bool: ...
