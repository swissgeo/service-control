from functools import lru_cache

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import ValidationError

from cognito.utils.client import Client
from config.authorization import VPAction
from organization.api import unit_to_response
from organization.models import Organization, Unit
from user.extra_audience import add_extra_audience
from user.models import AccessRequest, HumanUser, MachineUser, Role
from user.schemas import (
    AccessRequestListSchema,
    AccessRequestSchema,
    CreateAccessRequestSchema,
    CreateMachineUserSchema,
    MachineUserListSchema,
    MachineUserSchema,
    RoleListSchema,
    RoleSchema,
    UpdateAccessRequestSchema,
    UpdateUserSchema,
    UserListSchema,
    UserSchema,
)
from utils import api_path
from utils.auth import is_authenticated, vp_auth
from utils.language import LanguageCode, get_language, get_translation

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


@lru_cache(maxsize=2 ** len(Role.all()))  # all possible combinations of roles for caching
def map_role_ids_to_response(role_ids: tuple[str, ...]) -> list[RoleSchema]:
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
    request_user = request.user

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
    """List human users of organization."""

    lang_to_use = get_language(lang, request.headers)
    org = get_object_or_404(Organization, organization_id=organization_id)
    users = HumanUser.objects.filter(organization=org).order_by("last_name", "first_name")
    response = [
        UserSchema(
            id=user.sub,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            roles=map_role_ids_to_response(tuple(user.roles)),
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
    """Update roles of human user."""

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
        roles=map_role_ids_to_response(tuple(user.roles)),
        unit=unit_to_response(user.unit, lang=lang_to_use) if user.unit else None,
    )


@router.delete(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/users/{{{api_path.User.parameter_name}}}",
    exclude_none=True,
    auth=vp_auth(VPAction.UPDATE_USER),
)
def remove_user(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,
    user_id: str,
) -> HttpResponse:
    """
    Remove human user from organization. This does not delete the user in cognito but
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


@router.post(
    "/accessrequests",
    exclude_none=True,
    response={201: AccessRequestSchema},
    auth=is_authenticated,
)
def create_access_request(
    request: HttpRequest,
    access_request_in: CreateAccessRequestSchema,
    lang: LanguageCode | None = None,
) -> AccessRequestSchema:
    """
    Create an access request to an organization for the user.
    """

    lang_to_use = get_language(lang, request.headers)
    organization = get_object_or_404(
        Organization, organization_id=access_request_in.organization_id
    )
    access_request = AccessRequest.objects.create(
        user=request.user,
        organization=organization,
        state=AccessRequest.AccessRequestState.PENDING.value,
    )

    return AccessRequestSchema(
        id=access_request.access_request_id,
        organization_id=access_request.organization.organization_id,
        organization_acronym=get_translation(access_request.organization, "acronym", lang_to_use),
        organization_name=get_translation(access_request.organization, "name", lang_to_use),
        state=access_request.state,
        created=access_request.created.isoformat(),
    )


@router.get(
    "/accessrequests",
    exclude_none=True,
    response={200: AccessRequestListSchema},
    auth=is_authenticated,
)
def list_access_requests(
    request: HttpRequest,
    lang: LanguageCode | None = None,
) -> AccessRequestListSchema:
    """
    List all access requests for the authenticated user.
    """

    lang_to_use = get_language(lang, request.headers)
    access_requests = AccessRequest.objects.filter(user=request.user)

    return AccessRequestListSchema(
        items=[
            AccessRequestSchema(
                id=ar.access_request_id,
                organization_id=ar.organization.organization_id,
                organization_acronym=get_translation(ar.organization, "acronym", lang_to_use),
                organization_name=get_translation(ar.organization, "name", lang_to_use),
                state=ar.state,
                created=ar.created.isoformat(),
            )
            for ar in access_requests
        ]
    )


@router.put(
    "/accessrequests/{access_request_id}",
    exclude_none=True,
    response={200: AccessRequestSchema},
    auth=is_authenticated,
)
def update_access_request(
    request: HttpRequest,
    access_request_id: str,
    access_request_in: UpdateAccessRequestSchema,
    lang: LanguageCode | None = None,
) -> AccessRequestSchema:
    """
    Cancel an access request for the authenticated user.
    """

    lang_to_use = get_language(lang, request.headers)
    access_request = get_object_or_404(
        AccessRequest, access_request_id=access_request_id, user=request.user
    )
    if access_request.state != AccessRequest.AccessRequestState.PENDING.value:
        raise ValidationError(errors=[{"state": "Only pending access requests can be updated"}])
    if access_request_in.state != AccessRequest.AccessRequestState.CANCELLED.value:
        raise ValidationError(errors=[{"state": "Can only update state to cancelled"}])

    access_request.state = AccessRequest.AccessRequestState.CANCELLED.value
    access_request.save()

    return AccessRequestSchema(
        id=access_request.access_request_id,
        organization_id=access_request.organization.organization_id,
        organization_acronym=get_translation(access_request.organization, "acronym", lang_to_use),
        organization_name=get_translation(access_request.organization, "name", lang_to_use),
        state=access_request.state,
        created=access_request.created.isoformat(),
    )


@router.get(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/accessrequests",
    response={200: AccessRequestListSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.UPDATE_USER),
)
def list_access_requests_for_organization(
    request: HttpRequest,
    organization_id: str,
    lang: LanguageCode | None = None,
) -> AccessRequestListSchema:
    """
    List all access requests for an organization.
    """

    lang_to_use = get_language(lang, request.headers)
    org = get_object_or_404(Organization, organization_id=organization_id)
    access_requests = AccessRequest.objects.filter(organization=org).order_by("-created")

    return AccessRequestListSchema(
        items=[
            AccessRequestSchema(
                id=ar.access_request_id,
                organization_id=ar.organization.organization_id,
                organization_acronym=get_translation(ar.organization, "acronym", lang_to_use),
                organization_name=get_translation(ar.organization, "name", lang_to_use),
                state=ar.state,
                created=ar.created.isoformat(),
                user=UserSchema(
                    id=ar.user.sub,
                    email=ar.user.email,
                    first_name=ar.user.first_name,
                    last_name=ar.user.last_name,
                    roles=map_role_ids_to_response(tuple(ar.user.roles)),
                    unit=unit_to_response(ar.user.unit, lang=lang_to_use) if ar.user.unit else None,
                )
                if ar.user
                else None,
            )
            for ar in access_requests
        ]
    )


@router.put(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/accessrequests/{{access_request_id}}",
    response={200: AccessRequestSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.UPDATE_USER),
)
def update_access_request_for_organization(
    request: HttpRequest,
    organization_id: str,
    access_request_id: str,
    access_request_in: UpdateAccessRequestSchema,
    lang: LanguageCode | None = None,
) -> AccessRequestSchema:
    """
    Approve or decline an access request for an organization.
    """

    lang_to_use = get_language(lang, request.headers)
    org = get_object_or_404(Organization, organization_id=organization_id)
    access_request = get_object_or_404(
        AccessRequest, organization=org, access_request_id=access_request_id
    )

    if access_request.state != AccessRequest.AccessRequestState.PENDING.value:
        raise ValidationError(errors=[{"state": "Only pending access requests can be updated"}])
    if access_request_in.state not in [
        AccessRequest.AccessRequestState.APPROVED.value,
        AccessRequest.AccessRequestState.DECLINED.value,
    ]:
        raise ValidationError(errors=[{"state": "Can only update state to approved or declined"}])

    # At least for now we don't use a database transaction here as adding a user to and organization
    # triggers changes in cognito which should not be done within a database transaction.
    if access_request_in.state == AccessRequest.AccessRequestState.APPROVED.value:
        access_request.user.organization = access_request.organization
        if not access_request_in.roles or len(access_request_in.roles) == 0:
            raise ValidationError(
                errors=[
                    {"roles": "At least 1 role must be assigned when approving an access request"}
                ]
            )
        access_request.user.roles = access_request_in.roles
        if access_request_in.unit_id:
            unit = get_object_or_404(
                Unit, organization=access_request.organization, unit_id=access_request_in.unit_id
            )
            access_request.user.unit = unit
        else:
            access_request.user.unit = None
        access_request.user.save()

    access_request.state = access_request_in.state
    access_request.save()

    return AccessRequestSchema(
        id=access_request.access_request_id,
        organization_id=access_request.organization.organization_id,
        organization_acronym=get_translation(access_request.organization, "acronym", lang_to_use),
        organization_name=get_translation(access_request.organization, "name", lang_to_use),
        state=access_request.state,
        created=access_request.created.isoformat(),
        user=UserSchema(
            id=access_request.user.sub,
            email=access_request.user.email,
            first_name=access_request.user.first_name,
            last_name=access_request.user.last_name,
            roles=map_role_ids_to_response(tuple(access_request.user.roles))
            if access_request.user.roles
            else [],
            unit=unit_to_response(access_request.user.unit, lang=lang_to_use)
            if access_request.user.unit
            else None,
        )
        if access_request.user
        else None,
    )
