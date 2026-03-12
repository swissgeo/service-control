from enum import Enum
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from django.http import HttpRequest


class Parameter(Enum):
    """Parameter represents a path variable in the API that identifies an entity in the verified
    permissions policy store.
    """

    ORGANIZATION = ("organization_id", "Organization", [])
    UNIT = ("unit_id", "Unit", ["ORGANIZATION"])
    MACHINE_USER = ("machine_user_id", "MachineUser", ["ORGANIZATION"])

    def __new__(cls, parameter_name: str, _entity_type: str, _parent_names: list[str]) -> Self:
        obj = object.__new__(cls)
        obj._value_ = parameter_name
        return obj

    def __init__(self, parameter_name: str, entity_type: str, parent_names: list[str]) -> None:
        self.parameter_name = parameter_name  # The name of the path variable in the API path
        self.entity_type = entity_type  # Entity name in verified permissions policy store
        self.parent_names = parent_names

    @property
    def parents(self) -> list[Parameter]:
        return [Parameter[name] for name in self.parent_names]

    def vp_entity(self, request: HttpRequest, namespace: str) -> dict:
        """Verified permissions entity representation for the parameter in the request."""
        if (resolver_match := request.resolver_match) and (
            resource_id := resolver_match.kwargs.get(self.parameter_name)
        ):
            return {
                "entityType": f"{namespace}::{self.entity_type}",
                "entityId": resource_id,
            }
        return {}

    def vp_entity_with_parents(self, request: HttpRequest, namespace: str) -> dict:
        """Verified permissions entity representation for the parameter in the request,
        including its parents.
        """
        return {
            "identifier": self.vp_entity(request, namespace),
            "parents": [p.vp_entity(request, namespace) for p in self.parents],
        }
