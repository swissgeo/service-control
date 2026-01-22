from cognito.utils.client import Client
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import ValidationError
from organization.models import Organization

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
    request: HttpRequest, organization_id: str, machine_user_in: CreateMachineUserSchema
) -> MachineUserSchema:
    """Create a Machine User.

    TODO: Authorization should only be available to organization admins.
    TODO: Add request body with authorization permissions for machine user and create respective
    policy in verified permissions.
    """

    _ = request

    org = get_object_or_404(Organization, organization_id=organization_id)

    # Check that no machine user already exists with same name
    try:
        # If user with same name already exists for this org, return error
        MachineUser.objects.get(organization=org, name=machine_user_in.name)
        raise ValidationError(errors=[{"name": "machine user with this name already exists"}])
    except MachineUser.DoesNotExist:
        pass

    # Create cognito app client
    cognito_client = Client()
    app_client = cognito_client.create_app_client(machine_user_in.name)

    # Save app client info in database
    MachineUser.objects.create(
        machine_user_id=app_client.client_id,
        name=app_client.name,
        created_by_user="Get user from header",
        organization=org,
    )

    return MachineUserSchema(
        name=app_client.name, client_id=app_client.client_id, client_secret=app_client.client_secret
    )


@router.get(
    "/organizations/{organization_id}/machineusers",
    response={200: MachineUserListSchema},
    exclude_none=True,
)
def machine_users(request: HttpRequest, organization_id: str) -> MachineUserListSchema:
    """List machine users of organization.

    TODO: Authorization should only be available to organization admins.
    """

    _ = request

    models = (
        MachineUser.objects.filter(organization__organization_id=organization_id)
        .order_by("name")
        .all()
    )
    response = [machine_user_to_response(model) for model in models]
    return MachineUserListSchema(items=response)
