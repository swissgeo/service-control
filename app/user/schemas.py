from ninja import Schema

from organization.schemas import UnitSchema  # noqa: TC001
from user.models import AccessRequest  # noqa: TC001


class MachineUserSchema(Schema):
    name: str
    client_id: str
    # client_secret only returned on initial creation of machine user
    client_secret: str | None = None


class MachineUserListSchema(Schema):
    items: list[MachineUserSchema]


class CreateMachineUserSchema(Schema):
    name: str
    token_duration_min: int | None = None


class RoleSchema(Schema):
    id: str
    name: str
    description: str


class RoleListSchema(Schema):
    items: list[RoleSchema]


class UserSchema(Schema):
    id: str
    email: str
    first_name: str
    last_name: str
    roles: list[RoleSchema]
    unit: UnitSchema | None = None


class UserListSchema(Schema):
    items: list[UserSchema]


class UpdateUserSchema(Schema):
    roles: list[str]
    unit_id: str | None = None


class CreateAccessRequestSchema(Schema):
    organization_id: str


class AccessRequestSchema(Schema):
    id: str
    organization_id: str
    organization_acronym: str
    organization_name: str
    state: AccessRequest.AccessRequestState
    created: str


class UpdateAccessRequestSchema(Schema):
    state: AccessRequest.AccessRequestState


class AccessRequestListSchema(Schema):
    items: list[AccessRequestSchema]
