from typing import Any
from unittest.mock import patch

from jwt import encode

from django.conf import settings
from django.contrib.auth.models import User

import pytest

from config.authorization import VPRole
from organization.models import Organization, Unit
from user.models import CustomUser


@pytest.fixture(name="organization")
def fixture_organization(db):
    with patch("organization.models.VPClient") as vp_client, patch("organization.models.Client"):
        vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id"
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
    with patch("organization.models.Client"):
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
def fixture_user(cognito_client, organization):
    auth_user = User.objects.create(
        username="user1",
        first_name="Chuck",
        last_name="Norris",
        email="c.n@example.com",
    )
    return CustomUser.objects.create(
        user=auth_user,
        user_type=CustomUser.UserType.HUMAN,
        organization=organization,
    )


@pytest.fixture(name="machine_user")
def fixture_machine_user(organization, user, django_machine_user_factory):
    return django_machine_user_factory(
        username="abc", name="Machine 1", organization=organization, created_by_user=user
    )


@pytest.fixture(name="user_headers")
@patch("user.models.Client")
def fixture_user_headers(cognito_client, django_user_model, organization):

    organization_admin = django_user_model.objects.create_user(
        username="organization_admin",
        password="password",
    )
    CustomUser.objects.create(
        user=organization_admin,
        organization=organization,
        roles=[VPRole.ORG_ADMIN],
    )
    # TODO: add organization user etc.

    return {
        "anonymous": {},
        "admin": {
            "X-Auth-Request-User": "admin",
            "X-Auth-Request-Groups": ",".join(settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS),
            "X-Auth-Request-Email": "admin@example.org",
            "X-Auth-Request-Preferred-Username": "prefix-admin",
            "X-Auth-Request-Access-Token": encode(
                {"first_name": "admin", "last_name": "admin"}, "key"
            ),
        },
        "user": {
            "X-Auth-Request-User": "user",
            "X-Auth-Request-Groups": "",
            "X-Auth-Request-Email": "user@example.org",
            "X-Auth-Request-Preferred-Username": "prefix-user",
            "X-Auth-Request-Access-Token": encode(
                {"first_name": "user", "last_name": "user"}, "key"
            ),
        },
        "organization_admin": {
            "X-Auth-Request-User": "organization_admin",
            "X-Auth-Request-Groups": "organization",
            "X-Auth-Request-Email": "organization_admin@example.org",
            "X-Auth-Request-Preferred-Username": "prefix-organization_admin",
            "X-Auth-Request-Access-Token": encode(
                {"first_name": "organization_admin", "last_name": "organization_admin"}, "key"
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
        username: str, name: str, organization: Organization, created_by_user: User
    ) -> Any:
        return CustomUser.objects.create(
            user=User.objects.create_user(username=username, last_name=name),
            user_type=CustomUser.UserType.MACHINE,
            organization=organization,
            created_by_user=created_by_user,
        )

    return create_machine_user
