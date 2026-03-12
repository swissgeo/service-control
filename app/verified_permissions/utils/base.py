from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest

    from utils.api_path import Parameter


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
        resource: Parameter,
        request: HttpRequest,
    ) -> bool: ...
