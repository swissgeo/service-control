from organization.models import Organization
from pytest import fixture


@fixture(name='organization')
def fixture_organization(db):
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
