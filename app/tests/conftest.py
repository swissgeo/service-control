from unittest.mock import patch

import pytest
from organization.models import Organization


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
