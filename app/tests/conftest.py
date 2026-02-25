from unittest.mock import patch

from jwt import encode

from django.conf import settings

import pytest

from organization.models import Organization, Unit
from user.models import CustomUser, MachineUser


@pytest.fixture(name="organization")
def fixture_organization(db):
    with patch("organization.models.Client"):
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


@pytest.fixture(name="machine_user")
def fixture_machine_user(organization):
    return MachineUser.objects.create(
        machine_user_id="abc", name="Machine 1", created_by_user="user1", organization=organization
    )


@pytest.fixture(name="user_headers")
def fixture_user_headers(django_user_model, organization):

    organization_admin = django_user_model.objects.create_user(
        username="organization_admin",
        password="password",
    )
    CustomUser.objects.create(
        user=organization_admin,
        organization=organization,
    )
    # TODO: make admin
    # TODO: add organization user etc.

    return {
        "anonymous": {},
        "admin": {
            "X-Auth-Request-User": "admin",
            "X-Auth-Request-Groups": ",".join(settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS),
            "X-Auth-Request-Email": "admin@example.org",
            "X-Auth-Request-Access-Token": encode(
                {"first_name": "admin", "last_name": "admin"}, "key"
            ),
        },
        "user": {
            "X-Auth-Request-User": "user",
            "X-Auth-Request-Groups": "",
            "X-Auth-Request-Email": "user@example.org",
            "X-Auth-Request-Access-Token": encode(
                {"first_name": "user", "last_name": "user"}, "key"
            ),
        },
        "organization_admin": {
            "X-Auth-Request-User": "organization_admin",
            "X-Auth-Request-Groups": "organization",
            "X-Auth-Request-Email": "organization_admin@example.org",
            "X-Auth-Request-Access-Token": encode(
                {"first_name": "organization_admin", "last_name": "organization_admin"}, "key"
            ),
        },
    }
