from abc import ABC, abstractmethod

from django.http import HttpRequest

from cognito.utils.client import OrganizationGroup, UnitGroup
from utils.api_path import Parameter


class BaseClient(ABC):
    @abstractmethod
    def create_org_admin_policy(self, user_group: OrganizationGroup) -> str: ...

    @abstractmethod
    def create_dataset_admin_policy(self, user_group: UnitGroup) -> str: ...

    @abstractmethod
    def create_dataset_contributor_policy(self, user_group: UnitGroup) -> str: ...

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
