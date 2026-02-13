from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import ValidationError

from cognito.utils.client import Client
from organization.models import Organization
from user.extra_audience import add_extra_audience
from user.models import CustomUser, Role
from user.schemas import (
    CreateMachineUserSchema,
    MachineUserListSchema,
    MachineUserSchema,
    RoleListSchema,
    RoleSchema,
)
from utils.auth import organization_admin_auth

router = Router()


def machine_user_to_response(model: CustomUser) -> MachineUserSchema:
    return MachineUserSchema(
        name=model.user.last_name,
        client_id=model.user.username,
    )


def role_to_response(model: Role) -> RoleSchema:
    return RoleSchema(
        id=model.role_id,
        name=model.name,
        description=model.description,
    )


@router.post(
    "/organizations/{organization_id}/machineusers",
    response={201: MachineUserSchema},
    exclude_none=True,
    auth=organization_admin_auth,
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
    existing_machine_user = CustomUser.objects.filter(
        organization__organization_id=organization_id,
        user_type=CustomUser.UserType.MACHINE,
        user__last_name=machine_user_in.name,
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
        base_user = User.objects.create(
            username=app_client.client_id,
            last_name=app_client.name,
        )
        new_machine_user = CustomUser.objects.create(
            user_type=CustomUser.UserType.MACHINE,
            user=base_user,
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
    "/organizations/{organization_id}/machineusers",
    response={200: MachineUserListSchema},
    exclude_none=True,
    auth=organization_admin_auth,
)
def machine_users(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,
) -> MachineUserListSchema:
    """
    List machine users of organization.
    """

    models = (
        CustomUser.objects.filter(
            organization__organization_id=organization_id, user_type=CustomUser.UserType.MACHINE
        )
        .order_by("user__last_name")
        .all()
    )
    response = [machine_user_to_response(model) for model in models]
    return MachineUserListSchema(items=response)


@router.delete(
    "/organizations/{organization_id}/machineusers/{machine_user_id}",
    exclude_none=True,
    auth=organization_admin_auth,
)
def delete_machine_users(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,  # noqa: ARG001  not used but in path
    machine_user_id: str,
) -> HttpResponse:
    """
    Delete machine user of organization.
    """
    machine_user_to_delete = get_object_or_404(
        CustomUser, user_type=CustomUser.UserType.MACHINE, user__username=machine_user_id
    )
    machine_user_to_delete.delete()

    return HttpResponse(status=204)


@router.get(
    "/roles",
    response={200: RoleListSchema},
    exclude_none=True,
)
def roles(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
) -> RoleListSchema:
    """List all available roles.

    TODO: Authorization is this public??
    """

    models = Role.objects.order_by("name").all()
    response = [role_to_response(model) for model in models]
    return RoleListSchema(items=response)
