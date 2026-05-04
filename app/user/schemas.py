import datetime
from functools import lru_cache

from pydantic import ConfigDict

from ninja import Field, Schema

from organization.schemas import UnitSchema
from schemas import ResolverContext
from user.models import AccessRequest, HumanUser, Role
from utils.language import get_language


class MachineUserSchema(Schema):
    name: str
    client_id: str = Field(alias="sub")
    # client_secret only returned on initial creation of machine user
    client_secret: str | None = None

    model_config = ConfigDict(
        # Required to construct schema from dict that uses client_id as key instead of sub.
        # This is needed when returning in the response of creating a machine user.
        populate_by_name=True
    )


class MachineUserListSchema(Schema):
    items: list[MachineUserSchema]


class CreateMachineUserSchema(Schema):
    name: str
    token_duration_min: int | None = None


class RoleSchema(Schema):
    id: str = Field(alias="role_id")
    name: str
    description: str


class RoleListSchema(Schema):
    items: list[RoleSchema]


@lru_cache(maxsize=2 ** len(Role.all()))  # all possible combinations of roles for caching
def map_role_ids_to_response(role_ids: tuple[str, ...]) -> list[Role]:
    role_by_id = {role.role_id: role for role in Role.all()}
    return [role_by_id[role_id] for role_id in role_ids if role_id in role_by_id]


class UserSchema(Schema):
    id: str = Field(alias="sub")
    email: str
    first_name: str
    last_name: str
    roles: list[RoleSchema]
    unit: UnitSchema | None = None

    @staticmethod
    def resolve_roles(obj: HumanUser) -> list[RoleSchema]:
        """Resolves value of roles field by mapping role ids to RoleSchema objects.
        Uses lru_cache to cache results for performance."""
        return map_role_ids_to_response(tuple(sorted(obj.roles)))


class UserListSchema(Schema):
    items: list[UserSchema]


class UpdateUserSchema(Schema):
    roles: list[str]
    unit_id: str | None = None


class CreateAccessRequestSchema(Schema):
    organization_id: str


class UserAccessRequestSchema(Schema):
    id: str = Field(alias="access_request_id")
    organization_id: str = Field(alias="organization.organization_id")
    organization_acronym: str
    organization_name: str
    state: AccessRequest.AccessRequestState
    created: datetime.datetime

    @staticmethod
    def resolve_organization_acronym(obj: AccessRequest, context: ResolverContext) -> str:
        """Resolves value of organization_acronym field by getting the acronym
        in the appropriate language based on the request context."""
        request = context["request"]
        lang = get_language(request.GET.get("lang"), request.headers)

        return getattr(obj.organization, f"acronym_{lang}")

    @staticmethod
    def resolve_organization_name(obj: AccessRequest, context: ResolverContext) -> str:
        """Resolves value of organization_name field by getting the name
        in the appropriate language based on the request context."""
        request = context["request"]
        lang = get_language(request.GET.get("lang"), request.headers)

        return getattr(obj.organization, f"name_{lang}")


class UserAccessRequestListSchema(Schema):
    items: list[UserAccessRequestSchema]


class UpdateAccessRequestSchema(Schema):
    state: AccessRequest.AccessRequestState
    roles: list[str] | None = None  # Only needed when approving an access request
    unit_id: str | None = None  # Only needed when approving an access request


class AccessRequestSchema(UserAccessRequestSchema):
    user: UserSchema


class AccessRequestListSchema(Schema):
    items: list[AccessRequestSchema]
