from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router

from cognito.utils.client import Client
from organization.models import Organization
from user.extra_audience import add_extra_audience, remove_extra_audience
from user.models import MachineUser
from user.schemas import CreateMachineUserSchema, MachineUserListSchema, MachineUserSchema

router = Router()


def machine_user_to_response(model: MachineUser) -> MachineUserSchema:
    return MachineUserSchema(
        name=model.name,
        client_id=model.machine_user_id,
    )


@router.post(
    "/organizations/{organization_id}/machineusers",
    response={201: MachineUserSchema},
    exclude_none=True,
)
def create_machine_user(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,
    machine_user_in: CreateMachineUserSchema,
) -> MachineUserSchema:
    """Create a Machine User.

    TODO: Authorization should only be available to organization admins.
    TODO: Add request body with authorization permissions for machine user and create respective
    policy in verified permissions.
    """

    org = get_object_or_404(Organization, organization_id=organization_id)

    # Create cognito app client
    cognito_client = Client()
    app_client = cognito_client.create_app_client(
        machine_user_in.name, machine_user_in.token_duration_min
    )

    try:
        # Save app client info in database
        new_machine_user = MachineUser.objects.create(
            machine_user_id=app_client.client_id,
            name=app_client.name,
            created_by_user="TODO: Get user from header",
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
)
def machine_users(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,
) -> MachineUserListSchema:
    """List machine users of organization.

    TODO: Authorization should only be available to organization admins.
    """

    models = (
        MachineUser.objects.filter(organization__organization_id=organization_id)
        .order_by("name")
        .all()
    )
    response = [machine_user_to_response(model) for model in models]
    return MachineUserListSchema(items=response)


@router.delete(
    "/organizations/{organization_id}/machineusers/{machine_user_id}",
    exclude_none=True,
)
def delete_machine_users(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,  # noqa: ARG001  not used but in path
    machine_user_id: str,
) -> HttpResponse:
    machine_user_to_delete = get_object_or_404(MachineUser, machine_user_id=machine_user_id)
    cognito_client = Client()

    # No exception handling on purpose, as if something fails, at least the
    # client may no longer have access.
    cognito_client.delete_app_client(machine_user_to_delete.machine_user_id)
    remove_extra_audience(machine_user_to_delete.machine_user_id)
    machine_user_to_delete.delete()

    return HttpResponse(status=204)
