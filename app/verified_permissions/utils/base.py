from abc import ABC, abstractmethod


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
