from typing import Any
from unittest.mock import patch

from jwt import encode

from django.conf import settings

import pytest

from config.authorization import VPRole
from organization.models import Organization, Unit
from user.models import CustomUser, HumanUser, MachineUser


@pytest.fixture(name="organization")
def fixture_organization(db):
    with patch("organization.models.VPClient") as vp_client, patch("organization.models.Client"):
        vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id"
        vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
        vp_client.return_value.create_dataset_contributor_policy.return_value = (
            "mock-contributor-policy-id"
        )
        yield Organization.objects.create(
            organization_id="ch.bafu",
            acronym_de="BAFU",
            acronym_fr="OFEV",
            acronym_en="FOEN",
            acronym_it="UFAM",
            acronym_rm="UFAM",
            name_de="Bundesamt für Umwelt",
            name_fr="Office fédéral de l'environnement",
            name_en="Federal Office for the Environment",
            name_it="Ufficio federale dell'ambiente",
            name_rm="Uffizi federal per l'ambient",
        )


@pytest.fixture(name="unit")
def fixture_unit(db, organization):
    with patch("organization.models.VPClient") as vp_client, patch("organization.models.Client"):
        vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
        vp_client.return_value.create_dataset_contributor_policy.return_value = (
            "mock-contributor-policy-id"
        )
        yield Unit.objects.create(
            organization=organization,
            unit_id="ch.bafu.fauna",
            name_de="Fauna",
            name_fr="Faune",
            name_en="Fauna",
            name_it="Fauna",
            name_rm="Fauna",
        )


@pytest.fixture(name="user")
@patch("user.models.Client")
def fixture_user(cognito_client, organization, unit):
    return HumanUser.objects.create(
        sub="1234",
        first_name="Chuck",
        last_name="Norris",
        email="c.n@example.com",
        cognito_username="c.norris",
        organization=organization,
        unit=unit,
        roles=[VPRole.DATASET_ADMIN],
    )


@pytest.fixture(name="user_without_org")
@patch("user.models.Client")
def fixture_new_user(cognito_client):
    return HumanUser.objects.create(
        sub="user_without_org",
        first_name="New",
        last_name="User",
        email="new_user@example.com",
        cognito_username="prefix-user_without_org",
    )


@pytest.fixture(name="machine_user")
def fixture_machine_user(organization, user, django_machine_user_factory):
    return django_machine_user_factory(
        app_id="abc", name="Machine 1", organization=organization, created_by_user=user
    )


@pytest.fixture(name="user_headers")
@patch("user.models.Client")
def fixture_user_headers(cognito_client, organization, user_without_org):

    HumanUser.objects.create(
        sub="organization_admin",
        cognito_username="prefix-organization_admin",
        first_name="Organization",
        last_name="Admin",
        email="organization_admin@example.org",
        organization=organization,
        roles=[VPRole.ORG_ADMIN],
    )
    HumanUser.objects.create(
        sub="organization_user",
        cognito_username="prefix-organization_user",
        first_name="Organization",
        last_name="User",
        email="organization_user@example.org",
        organization=organization,
        roles=[VPRole.DATASET_ADMIN],
    )

    return {
        "anonymous": {},
        "superuser": {
            "X-Auth-Request-User": "superuser",
            "X-Auth-Request-Groups": ",".join(settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS),
            "X-Auth-Request-Email": "superuser@example.org",
            "X-Auth-Request-Preferred-Username": "prefix-superuser",
            "X-Auth-Request-Access-Token": encode(
                {"first_name": "superuser", "last_name": "superuser"}, "key"
            ),
        },
        "user": {
            "X-Auth-Request-User": "organization_user",
            "X-Auth-Request-Groups": "",
            "X-Auth-Request-Email": "organization_user@example.org",
            "X-Auth-Request-Preferred-Username": "prefix-organization_user",
            "X-Auth-Request-Access-Token": encode(
                {"first_name": "Organization", "last_name": "User"}, "key"
            ),
        },
        "organization_admin": {
            "X-Auth-Request-User": "organization_admin",
            "X-Auth-Request-Groups": "organization",
            "X-Auth-Request-Email": "organization_admin@example.org",
            "X-Auth-Request-Preferred-Username": "prefix-organization_admin",
            "X-Auth-Request-Access-Token": encode(
                {"first_name": "Organization", "last_name": "Admin"}, "key"
            ),
        },
        "user_without_org": {
            "X-Auth-Request-User": user_without_org.sub,
            "X-Auth-Request-Groups": "",
            "X-Auth-Request-Email": user_without_org.email,
            "X-Auth-Request-Preferred-Username": user_without_org.cognito_username,
            "X-Auth-Request-Access-Token": encode(
                {
                    "first_name": user_without_org.first_name,
                    "last_name": user_without_org.last_name,
                },
                "key",
            ),
        },
    }


@pytest.fixture
def django_machine_user_factory(db):
    """A fixture to create machine users.

    Returns a callable that accepts a username, name, organization, and the user who created it.

    Example usage:

        def test_something(django_machine_user_factory):
            user = django_machine_user_factory('admin', 'Admin User', organization, user)

    """

    def create_machine_user(
        app_id: str, name: str, organization: Organization, created_by_user: CustomUser
    ) -> Any:
        return MachineUser.objects.create(
            sub=app_id,
            name=name,
            organization=organization,
            created_by_user=created_by_user,
        )

    return create_machine_user
