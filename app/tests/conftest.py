from unittest.mock import patch

import pytest

from organization.models import Organization, Unit
from user.models import MachineUser
from utils.testing import AsyncMagicMock


@pytest.fixture(name="organization")
def fixture_organization(db):
    with patch("organization.signals.Client", new_callable=AsyncMagicMock):
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
    with patch("organization.signals.Client", new_callable=AsyncMagicMock):
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
