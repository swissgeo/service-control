from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from django.http import HttpRequest


class VPEntityType(StrEnum):
    ORGANIZATION = "Organization"
    UNIT = "Unit"
    MACHINE_USER = "MachineUser"


class Parameter(BaseModel):
    """Parameter represents a path variable in the API that identifies an entity in the verified
    permissions policy store.
    """

    parameter_name: str
    vp_entity_type: VPEntityType
    parents: list[Parameter] = []

    def vp_entity(self, request: HttpRequest, namespace: str) -> dict:
        """Verified permissions entity representation for the parameter in the request."""
        if (resolver_match := request.resolver_match) and (
            resource_id := resolver_match.kwargs.get(self.parameter_name)
        ):
            return {
                "entityType": f"{namespace}::{self.vp_entity_type}",
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


Organization = Parameter(parameter_name="organization_id", vp_entity_type=VPEntityType.ORGANIZATION)
Unit = Parameter(parameter_name="unit_id", vp_entity_type=VPEntityType.UNIT, parents=[Organization])
Machine_user = Parameter(
    parameter_name="machine_user_id",
    vp_entity_type=VPEntityType.MACHINE_USER,
    parents=[Organization],
)
