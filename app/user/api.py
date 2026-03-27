from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import ValidationError

from cognito.utils.client import Client
from config.authorization import VPAction
from organization.api import unit_to_response
from organization.models import Organization, Unit
from user.extra_audience import add_extra_audience
from user.models import HumanUser, MachineUser, Role
from user.schemas import (
    CreateMachineUserSchema,
    MachineUserListSchema,
    MachineUserSchema,
    RoleListSchema,
    RoleSchema,
    UpdateUserSchema,
    UserListSchema,
    UserSchema,
)
from utils import api_path
from utils.auth import is_authenticated, vp_auth
from utils.language import LanguageCode, get_language

router = Router(tags=["users"])


def machine_user_to_response(model: MachineUser) -> MachineUserSchema:
    return MachineUserSchema(
        name=model.name,
        client_id=model.sub,
    )


def role_to_response(model: Role) -> RoleSchema:
    return RoleSchema(
        id=model.role_id,
        name=model.name,
        description=model.description,
    )


def map_role_ids_to_response(role_ids: list[str]) -> list[RoleSchema]:
    role_by_id = {role.role_id: role for role in Role.all()}
    return [role_to_response(role_by_id[role_id]) for role_id in role_ids if role_id in role_by_id]


@router.post(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/machineusers",
    response={201: MachineUserSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.CREATE_MACHINE_USER),
)
def create_machine_user(
    request: HttpRequest,
    organization_id: str,
    machine_user_in: CreateMachineUserSchema,
) -> MachineUserSchema:
    """Create a Machine User.

    TODO: Add request body with authorization permissions for machine user and create respective
    policy in verified permissions.
    """
    request_user = getattr(request.user, "customuser", None)

    org = get_object_or_404(Organization, organization_id=organization_id)
    existing_machine_user = MachineUser.objects.filter(
        organization__organization_id=organization_id,
        name=machine_user_in.name,
    ).exists()
    if existing_machine_user:
        raise ValidationError(errors=[{"name": "machine user with this name already exists"}])

    # Create cognito app client
    cognito_client = Client()
    app_client = cognito_client.create_app_client(
        machine_user_in.name, machine_user_in.token_duration_min
    )

    try:
        # Save app client info in database
        new_machine_user = MachineUser.objects.create(
            sub=app_client.client_id,
            name=app_client.name,
            created_by_user=request_user,
            organization=org,
        )
    except:
        cognito_client.delete_app_client(app_client.client_id)
        raise

    try:
        # Add client id for Oauth2-Proxy
        add_extra_audience(app_client.client_id)
    except:
        new_machine_user.delete()
        cognito_client.delete_app_client(app_client.client_id)
        raise

    return MachineUserSchema(
        name=app_client.name, client_id=app_client.client_id, client_secret=app_client.client_secret
    )


@router.get(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/machineusers",
    response={200: MachineUserListSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.LIST_MACHINE_USERS),
)
def machine_users(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,
) -> MachineUserListSchema:
    """
    List machine users of organization.
    """

    models = MachineUser.objects.filter(organization__organization_id=organization_id)
    response = [machine_user_to_response(model) for model in models]
    return MachineUserListSchema(items=response)


@router.delete(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/machineusers/{{{api_path.Machine_user.parameter_name}}}",
    exclude_none=True,
    auth=vp_auth(VPAction.DELETE_MACHINE_USER, resource=api_path.Machine_user),
)
def delete_machine_users(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,  # noqa: ARG001  not used but in path
    machine_user_id: str,
) -> HttpResponse:
    """
    Delete machine user of organization.
    """
    machine_user_to_delete = get_object_or_404(MachineUser, sub=machine_user_id)
    machine_user_to_delete.delete()

    return HttpResponse(status=204)


@router.get(
    "/roles",
    response={200: RoleListSchema},
    exclude_none=True,
    auth=is_authenticated,
)
def roles(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
) -> RoleListSchema:
    """List all available roles."""

    models = sorted(Role.all(), key=lambda role: role.name)
    response = [role_to_response(model) for model in models]
    return RoleListSchema(items=response)


@router.get(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/users",
    response={200: UserListSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.LIST_USERS),
)
def users(
    request: HttpRequest,
    organization_id: str,
    lang: LanguageCode | None = None,
) -> UserListSchema:
    """List users of organization."""

    lang_to_use = get_language(lang, request.headers)
    org = get_object_or_404(Organization, organization_id=organization_id)
    users = HumanUser.objects.filter(organization=org).order_by("last_name", "first_name")
    response = [
        UserSchema(
            id=user.sub,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            roles=map_role_ids_to_response(user.roles),
            unit=unit_to_response(user.unit, lang=lang_to_use) if user.unit else None,
        )
        for user in users
    ]
    return UserListSchema(items=response)


@router.put(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/users/{{{api_path.User.parameter_name}}}",
    response={200: UserSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.UPDATE_USER),
)
def update_user(
    request: HttpRequest,
    organization_id: str,
    user_id: str,
    user_in: UpdateUserSchema,
    lang: LanguageCode | None = None,
) -> UserSchema:
    """Update roles of user."""

    lang_to_use = get_language(lang, request.headers)
    org = get_object_or_404(Organization, organization_id=organization_id)
    user = get_object_or_404(HumanUser, organization=org, sub=user_id)
    if user_in.unit_id:
        unit = get_object_or_404(Unit, unit_id=user_in.unit_id)
        user.unit = unit
    else:
        user.unit = None
    user.roles = user_in.roles
    user.save()

    return UserSchema(
        id=user.sub,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        roles=map_role_ids_to_response(user.roles),
        unit=unit_to_response(user.unit, lang=lang_to_use) if user.unit else None,
    )


@router.delete(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/users/{{{api_path.User.parameter_name}}}",
    exclude_none=True,
    auth=vp_auth(VPAction.UPDATE_USER),
)
def delete_user(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,
    user_id: str,
) -> HttpResponse:
    """
    Remove user from organization. This does not delete the user in cognito but
    removes all roles and unit association.
    """
    user_to_delete = get_object_or_404(
        HumanUser, organization__organization_id=organization_id, sub=user_id
    )
    user_to_delete.roles = []
    user_to_delete.unit = None
    user_to_delete.organization = None
    user_to_delete.save()

    return HttpResponse(status=204)
