from typing import Any, TypedDict, cast

from django.conf import settings
from django.core.management.base import CommandError, CommandParser

from cognito.utils.client import Client as CognitoClient
from cognito.utils.client import OrganizationGroup
from config.authorization import VPRole
from organization.models import Organization
from user.models import HumanUser
from utils.command import CustomBaseCommand


class OrganizationSeed(TypedDict):
    organization_id: str
    name_de: str
    name_fr: str
    name_en: str
    name_it: str
    name_rm: str
    acronym_de: str
    acronym_fr: str
    acronym_en: str
    acronym_it: str
    acronym_rm: str


class UserSeed(TypedDict):
    sub: str
    username: str
    first_name: str
    last_name: str
    email: str
    organization_id: str | None
    roles: list[str]


ORGANIZATIONS: list[OrganizationSeed] = [
    {
        "organization_id": "ch.bafu",
        "name_de": "Bundesamt für Umwelt",
        "name_fr": "Office fédéral de l'environnement",
        "name_en": "Federal Office for the Environment",
        "name_it": "Ufficio federale dell'ambiente",
        "name_rm": "Uffizi federal per l'ambient",
        "acronym_de": "BAFU",
        "acronym_fr": "OFEV",
        "acronym_en": "FOEN",
        "acronym_it": "UFAM",
        "acronym_rm": "UFAM",
    },
    {
        "organization_id": "ch.swisstopo",
        "name_de": "Bundesamt für Landestopografie swisstopo",
        "name_fr": "Office fédéral de topographie swisstopo",
        "name_en": "Federal Office of Topography swisstopo",
        "name_it": "Ufficio federale di topografia swisstopo",
        "name_rm": "Uffizi federal da topografia swisstopo",
        "acronym_de": "swisstopo",
        "acronym_fr": "swisstopo",
        "acronym_en": "swisstopo",
        "acronym_it": "swisstopo",
        "acronym_rm": "swisstopo",
    },
]

USERS: list[UserSeed] = [
    {
        "sub": "superuser",
        "username": "superuser",
        "first_name": "Super",
        "last_name": "User",
        "email": "superuser@example.org",
        "organization_id": None,
        "roles": [],
    },
    {
        "sub": "admin-bafu",
        "username": "admin.bafu",
        "first_name": "Admin",
        "last_name": "Bafu",
        "email": "admin.bafu@example.org",
        "organization_id": "ch.bafu",
        "roles": [VPRole.ORG_ADMIN.value],
    },
    {
        "sub": "user-bafu",
        "username": "user.bafu",
        "first_name": "User",
        "last_name": "Bafu",
        "email": "user.bafu@example.org",
        "organization_id": "ch.bafu",
        "roles": [VPRole.DATASET_ADMIN.value],
    },
    {
        "sub": "admin-swisstopo",
        "username": "admin.swisstopo",
        "first_name": "Admin",
        "last_name": "Swisstopo",
        "email": "admin.swisstopo@example.org",
        "organization_id": "ch.swisstopo",
        "roles": [VPRole.ORG_ADMIN.value],
    },
    {
        "sub": "user-swisstopo",
        "username": "user.swisstopo",
        "first_name": "User",
        "last_name": "Swisstopo",
        "email": "user.swisstopo@example.org",
        "organization_id": "ch.swisstopo",
        "roles": [VPRole.DATASET_ADMIN.value],
    },
]


class Command(CustomBaseCommand):
    """Seed local development test data for organizations and users."""

    help = "Seed local users and organizations in Cognito and PostgreSQL"

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing seeded users/organizations before seeding.",
        )
        parser.add_argument(
            "--recreate-cognito-users",
            action="store_true",
            help=(
                "With --reset, also delete and recreate cognito users. "
                "If omitted, cognito users are kept so their sub stays stable."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        self._validate_local_environment()
        cognito_client = CognitoClient()

        if options["reset"]:
            self._reset_seed_data(
                cognito_client,
                recreate_cognito_users=options["recreate_cognito_users"],
            )

        organizations = self._ensure_organizations()

        for user in USERS:
            sub = self._ensure_cognito_user(cognito_client, user)
            organization = None
            if user["organization_id"] is not None:
                organization = organizations[user["organization_id"]]
                self._ensure_cognito_group_membership(
                    cognito_client,
                    username=user["username"],
                    organization_id=organization.organization_id,
                )
            self._ensure_human_user(sub=sub, user=user, organization=organization)

            # Keep local cognito custom:roles in sync with service-control role assignments.
            cognito_client.update_user_roles(username=user["username"], roles=user["roles"])

        self.print_success(
            "Seeded %s organizations and %s users",
            len(ORGANIZATIONS),
            len(USERS),
        )

    def _reset_seed_data(
        self,
        cognito_client: CognitoClient,
        recreate_cognito_users: bool,
    ) -> None:
        for user in USERS:
            username = user["username"]

            deleted_users, _ = HumanUser.objects.filter(cognito_username=username).delete()
            if deleted_users:
                self.print("Deleted local user %s", username)

            if recreate_cognito_users:
                try:
                    cognito_client.client.admin_delete_user(
                        UserPoolId=cognito_client.user_pool_id,
                        Username=username,
                    )
                    self.print("Deleted cognito user %s", username)
                except cognito_client.client.exceptions.UserNotFoundException:
                    self.print("Cognito user %s not found during reset", username)
            else:
                self.print(
                    "Keeping cognito user %s to preserve stable sub",
                    username,
                )

        for org_data in ORGANIZATIONS:
            org_id = org_data["organization_id"]
            deleted_orgs, _ = Organization.objects.filter(organization_id=org_id).delete()
            if deleted_orgs:
                self.print("Deleted organization %s", org_id)

        self.print_success("Reset complete, applying seed data")

    def _validate_local_environment(self) -> None:
        endpoint = settings.COGNITO_ENDPOINT_URL.lower()
        is_local_endpoint = "localhost" in endpoint or "127.0.0.1" in endpoint
        if not is_local_endpoint:
            raise CommandError("Refusing to seed non-local Cognito endpoint.")

    def _ensure_organizations(self) -> dict[str, Organization]:
        organizations: dict[str, Organization] = {}
        for org_data in ORGANIZATIONS:
            organization, created = Organization.objects.update_or_create(
                organization_id=org_data["organization_id"],
                defaults={
                    "name_de": org_data["name_de"],
                    "name_fr": org_data["name_fr"],
                    "name_en": org_data["name_en"],
                    "name_it": org_data["name_it"],
                    "name_rm": org_data["name_rm"],
                    "acronym_de": org_data["acronym_de"],
                    "acronym_fr": org_data["acronym_fr"],
                    "acronym_en": org_data["acronym_en"],
                    "acronym_it": org_data["acronym_it"],
                    "acronym_rm": org_data["acronym_rm"],
                },
            )
            self.print(
                "%s organization %s",
                "Created" if created else "Updated",
                organization.organization_id,
            )
            organizations[organization.organization_id] = organization
        return organizations

    def _ensure_cognito_user(self, cognito_client: CognitoClient, user: UserSeed) -> str:
        username = user["username"]
        desired_sub = user["sub"]
        user_pool_id = cognito_client.user_pool_id

        try:
            response = cognito_client.client.admin_get_user(
                UserPoolId=user_pool_id,
                Username=username,
            )
            self.print("Found cognito user %s", username)
        except cognito_client.client.exceptions.UserNotFoundException:
            cognito_client.client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=username,
                TemporaryPassword="ChangeMe123!",
                MessageAction="SUPPRESS",
                UserAttributes=[
                    {"Name": "sub", "Value": desired_sub},
                    {"Name": "given_name", "Value": user["first_name"]},
                    {"Name": "family_name", "Value": user["last_name"]},
                    {"Name": "email", "Value": user["email"]},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "preferred_username", "Value": username},
                ],
            )
            cognito_client.client.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=username,
                Password="ChangeMe123!",  # noqa: S106 local-only development seed value
                Permanent=True,
            )
            response = cognito_client.client.admin_get_user(
                UserPoolId=user_pool_id,
                Username=username,
            )
            self.print_success("Created cognito user %s", username)

        attributes = cast("list[dict[str, Any]]", response.get("UserAttributes", []))
        sub = self._attribute_value(attributes, "sub")
        if not sub:
            raise CommandError(f"Missing sub attribute for cognito user '{username}'")

        if sub != desired_sub:
            raise CommandError(
                f"User '{username}' has sub '{sub}', expected '{desired_sub}'. "
                "Run with --reset --recreate-cognito-users to recreate with deterministic sub."
            )

        return sub

    def _ensure_cognito_group_membership(
        self,
        cognito_client: CognitoClient,
        username: str,
        organization_id: str,
    ) -> None:
        group = OrganizationGroup(organization_id)
        if cognito_client.create_group(group):
            self.print("Created cognito group %s", group.name)
        cognito_client.add_user_to_group(username=username, group=group)
        self.print("Ensured cognito group membership %s -> %s", username, group.name)

    def _ensure_human_user(
        self,
        sub: str,
        user: UserSeed,
        organization: Organization | None,
    ) -> None:
        human_user, created = HumanUser.objects.update_or_create(
            cognito_username=user["username"],
            defaults={
                "sub": sub,
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "email": user["email"],
                "organization": organization,
                "roles": user["roles"],
            },
        )

        self.print(
            "%s local user %s (%s)",
            "Created" if created else "Updated",
            human_user.cognito_username,
            organization.organization_id if organization else "No organization",
        )

    @staticmethod
    def _attribute_value(attributes: list[dict[str, Any]], name: str) -> str | None:
        for attribute in attributes:
            if attribute.get("Name") == name:
                return attribute.get("Value")
        return None
