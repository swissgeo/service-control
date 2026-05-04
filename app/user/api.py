from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import ValidationError

from cognito.utils.client import Client
from config.authorization import VPAction
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
    UpdateAccessRequestSchema,
    UpdateUserSchema,
    UserAccessRequestListSchema,
    UserAccessRequestSchema,
    UserListSchema,
    UserSchema,
)
from utils import api_path
from utils.auth import is_authenticated, vp_auth
from utils.exceptions import ConflictError
from utils.language import LanguageCode

router = Router(tags=["Auth"])


@router.post(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/machineusers",
    summary="Create machine user",
    tags=["Machine Users"],
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

    return MachineUserSchema.model_validate(
        {
            "name": app_client.name,
            "client_id": app_client.client_id,
            "client_secret": app_client.client_secret,
        }
    )


@router.get(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/machineusers",
    summary="List machine users",
    tags=["Machine Users"],
    response={200: MachineUserListSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.LIST_MACHINE_USERS),
)
def machine_users(
    request: HttpRequest,
    organization_id: str,
) -> dict[str, Any]:
    """
    List machine users of organization.
    """

    models = MachineUser.objects.filter(organization__organization_id=organization_id)
    return {"items": models}


@router.delete(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/machineusers/{{{api_path.Machine_user.parameter_name}}}",
    summary="Delete machine user",
    tags=["Machine Users"],
    exclude_none=True,
    auth=vp_auth(VPAction.DELETE_MACHINE_USER, resource=api_path.Machine_user),
)
def delete_machine_users(
    request: HttpRequest,
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
    summary="List roles",
    response={200: RoleListSchema},
    exclude_none=True,
    auth=is_authenticated,
)
def roles(
    request: HttpRequest,
) -> dict[str, Any]:
    """List all available roles."""

    models = sorted(Role.all(), key=lambda role: role.name)
    # response = [role_to_response(model) for model in models]
    return {"items": models}


@router.get(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/users",
    summary="List users",
    tags=["Users"],
    response={200: UserListSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.LIST_USERS),
)
def users(
    request: HttpRequest,
    organization_id: str,
    lang: LanguageCode | None = None,
) -> dict[str, Any]:
    """List human users of organization."""

    org = get_object_or_404(Organization, organization_id=organization_id)
    users = HumanUser.objects.filter(organization=org).order_by("last_name", "first_name")
    return {"items": users}


@router.put(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/users/{{{api_path.User.parameter_name}}}",
    summary="Update user",
    tags=["Users"],
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
) -> HumanUser:
    """Update roles of human user."""

    org = get_object_or_404(Organization, organization_id=organization_id)
    user = get_object_or_404(HumanUser, organization=org, sub=user_id)
    if user_in.unit_id:
        unit = get_object_or_404(Unit, unit_id=user_in.unit_id)
        user.unit = unit
    else:
        user.unit = None
    user.roles = user_in.roles
    user.save()

    return user


@router.delete(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/users/{{{api_path.User.parameter_name}}}",
    summary="Remove user",
    tags=["Users"],
    exclude_none=True,
    auth=vp_auth(VPAction.UPDATE_USER),
)
def remove_user(
    request: HttpRequest,
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
    summary="Create access request",
    tags=["Access Requests"],
    exclude_none=True,
    response={201: UserAccessRequestSchema},
    auth=is_authenticated,
)
def create_access_request(
    request: HttpRequest,
    access_request_in: CreateAccessRequestSchema,
    lang: LanguageCode | None = None,
) -> AccessRequest:
    """
    Create an access request to an organization for the user.
    """

    organization = get_object_or_404(
        Organization, organization_id=access_request_in.organization_id
    )
    return AccessRequest.objects.create(
        user=request.user,
        organization=organization,
        state=AccessRequest.AccessRequestState.PENDING.value,
    )


@router.get(
    "/accessrequests",
    summary="List access requests of user",
    tags=["Access Requests"],
    exclude_none=True,
    response={200: UserAccessRequestListSchema},
    auth=is_authenticated,
)
def list_access_requests(
    request: HttpRequest,
    lang: LanguageCode | None = None,
) -> dict[str, Any]:
    """
    List all access requests for the authenticated user.
    """

    access_requests = AccessRequest.objects.filter(user=request.user)

    return {"items": access_requests}


@router.put(
    "/accessrequests/{access_request_id}",
    summary="Cancel access request",
    tags=["Access Requests"],
    exclude_none=True,
    response={200: UserAccessRequestSchema},
    auth=is_authenticated,
)
def update_access_request(
    request: HttpRequest,
    access_request_id: str,
    access_request_in: UpdateAccessRequestSchema,
    lang: LanguageCode | None = None,
) -> AccessRequest:
    """
    Cancel an access request for the authenticated user.
    """

    access_request = get_object_or_404(
        AccessRequest, access_request_id=access_request_id, user=request.user
    )
    if access_request.state != AccessRequest.AccessRequestState.PENDING.value:
        raise ValidationError(errors=[{"state": "Only pending access requests can be updated"}])
    if access_request_in.state != AccessRequest.AccessRequestState.CANCELLED.value:
        raise ValidationError(errors=[{"state": "Can only update state to cancelled"}])

    access_request.state = AccessRequest.AccessRequestState.CANCELLED.value
    access_request.save()

    return access_request


@router.get(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/accessrequests",
    summary="List access requests for organization",
    tags=["Access Requests"],
    response={200: AccessRequestListSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.UPDATE_USER),
)
def list_access_requests_for_organization(
    request: HttpRequest,
    organization_id: str,
    lang: LanguageCode | None = None,
) -> dict[str, Any]:
    """
    List all access requests for an organization.
    """

    org = get_object_or_404(Organization, organization_id=organization_id)
    access_requests = AccessRequest.objects.filter(organization=org).order_by("-created")

    return {"items": access_requests}


@router.put(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/accessrequests/{{access_request_id}}",
    summary="Update access request for organization",
    tags=["Access Requests"],
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
) -> AccessRequest:
    """
    Approve or decline an access request for an organization.
    """

    org = get_object_or_404(Organization, organization_id=organization_id)
    access_request = get_object_or_404(
        AccessRequest, organization=org, access_request_id=access_request_id
    )

    if access_request.state != AccessRequest.AccessRequestState.PENDING.value:
        raise ConflictError("Only pending access requests can be updated")
    if access_request_in.state not in [
        AccessRequest.AccessRequestState.APPROVED.value,
        AccessRequest.AccessRequestState.DECLINED.value,
    ]:
        raise ValidationError(errors=[{"state": "Can only update state to approved or declined"}])

    # At least for now we don't use a database transaction here as adding a user to and organization
    # triggers changes in cognito which should not be done within a database transaction.
    # See GPS-632.
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

    return access_request
