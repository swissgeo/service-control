import re
from decimal import Decimal
from io import StringIO
from json import dumps
from unittest.mock import Mock, patch

from iso639 import Lang

from django.core.management import call_command

from dataservice.models import Dataservice, WMSDataservice
from dataset.models import Dataset, DatasetToContact, DatasetToDataset, DatasetToUnit
from distribution.models import Distribution, ExternalStacDistribution, ExternalWMSDistribution
from harvest.models import (
    DatasetMapping,
    DatasetToContactMapping,
    DatasetToUnitMapping,
    OrganizationMapping,
)
from organization.models import Contact, Organization, Unit
from thesaurus.models import Thesaurus


def api_response(services, config=None, capabilities=None):
    """Creates an API mock with the given responses.

    The arguments can either be a dictionary with the responses per language, or a dictionary with
    on response taken for all languages.

    Use it like this:

        with patch("harvest.management.commands.import_geodienste.get"):
            mock.side_effect = api_response(...)

    """

    def side_effect(url, timeout) -> dict:
        mock = Mock()

        if "services" in url:
            response = services
            language = url[-2:]
            mock.json.return_value = response.get(language, response)
        elif "viewer_config" in url:
            response = config or {}
            language = url[-2:]
            mock.json.return_value = response.get(language, response)
        elif "GetCapabilities" in url:
            response = capabilities or {}
            match = re.match(r".*/(deu|fra|eng|ita)\?.*", url)
            language = Lang(pt3=match.groups()[0]).pt1
            mock.status_code = 200
            mock.content = response.get(language, response)
        else:
            raise NotImplementedError(f"Don't know how to handle request to {url}")

        return mock

    return side_effect


# --------------------------------------------------------------------------------------------------
# Organizations
# --------------------------------------------------------------------------------------------------
@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_aggregate_organization(mock, client, db):
    mock.side_effect = api_response(
        {"services": [{"base_topic": "av", "canton": "LU", "broker": None}]}
    )

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.kgk does not exist yet, creating a new one" in out

    org = Organization.objects.get(organization_id="ch.kgk")
    assert org.name_de == "Konferenz der kantonalen Geoinformations- und Katasterstellen"
    assert org.name_fr == "Conférence des services cantonaux de la Géoinformation et du Cadastre"
    assert org.name_en == "Konferenz der kantonalen Geoinformations- und Katasterstellen"
    assert org.name_it == "Conferenza dei servizi cantonali per la Geoinformazione e del Catasto"
    assert org.name_rm == "Conferenza dals posts chantunals da Geoinfurmaziun e Cataster"
    assert org.acronym_de == "KGK"
    assert org.acronym_fr == "CGC"
    assert org.acronym_en == "KGK"
    assert org.acronym_it == "CGC"
    assert org.acronym_rm == "CGC"
    assert org.data_source == Organization.DataSource.GEODIENSTE
    assert org.data_source_ids == ["KGK"]

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.kgk already exists" in out


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_updates_aggregate_organization(mock, client, db):
    org = Organization(
        organization_id="ch.kgk",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DataSource.GEODIENSTE,
        data_source_ids=["KGK"],
    )
    org.save()

    mock.side_effect = api_response(
        {"services": [{"base_topic": "av", "canton": "LU", "broker": None}]}
    )

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.kgk already exists" in out
    assert "Organization ch.kgk updated" in out

    org.refresh_from_db()
    assert org.name_de == "Konferenz der kantonalen Geoinformations- und Katasterstellen"
    assert org.name_fr == "Conférence des services cantonaux de la Géoinformation et du Cadastre"
    assert org.name_en == "Konferenz der kantonalen Geoinformations- und Katasterstellen"
    assert org.name_it == "Conferenza dei servizi cantonali per la Geoinformazione e del Catasto"
    assert org.name_rm == "Conferenza dals posts chantunals da Geoinfurmaziun e Cataster"
    assert org.acronym_de == "KGK"
    assert org.acronym_fr == "CGC"
    assert org.acronym_en == "KGK"
    assert org.acronym_it == "CGC"
    assert org.acronym_rm == "CGC"
    assert org.data_source == Organization.DataSource.GEODIENSTE
    assert org.data_source_ids == ["KGK"]

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.kgk already exists" in out
    assert "Organization ch.kgk updated" not in out


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_uses_aggregate_organization_mapping(mock, client, db):
    org = Organization(
        organization_id="ch.kgk-cgc",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DataSource.USER_INPUT,
        data_source_ids=[],
    )
    org.save()

    mapping = OrganizationMapping(
        provider_id_prefix="KGK", organization_id="ch.kgk-cgc", update=False
    )
    mapping.save()

    mock.side_effect = api_response(
        {"services": [{"base_topic": "av", "canton": "LU", "broker": None}]}
    )

    # ---------
    # No update
    # ---------
    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id KGK: ch.kgk-cgc" in out
    assert "Organization ch.kgk-cgc updated" not in out

    org.refresh_from_db()
    assert org.name_de == "x"

    # ---------
    # Update
    # ---------
    mapping.update = True
    mapping.save()

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id KGK: ch.kgk-cgc" in out
    assert "Organization ch.kgk-cgc updated" in out

    org.refresh_from_db()
    assert org.name_de == "Konferenz der kantonalen Geoinformations- und Katasterstellen"
    assert org.name_fr == "Conférence des services cantonaux de la Géoinformation et du Cadastre"
    assert org.name_en == "Konferenz der kantonalen Geoinformations- und Katasterstellen"
    assert org.name_it == "Conferenza dei servizi cantonali per la Geoinformazione e del Catasto"
    assert org.name_rm == "Conferenza dals posts chantunals da Geoinfurmaziun e Cataster"
    assert org.acronym_de == "KGK"
    assert org.acronym_fr == "CGC"
    assert org.acronym_en == "KGK"
    assert org.acronym_it == "CGC"
    assert org.acronym_rm == "CGC"

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id KGK: ch.kgk-cgc" in out
    assert "Organization with organization_id ch.kgk updated" not in out


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_cantonal_organization(mock, client, db):
    mock.side_effect = api_response(
        {"services": [{"base_topic": "av", "canton": "LU", "broker": None}]}
    )

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert (
        "Organization with organization_id ch.geodienste-lu does not exist yet, creating a new one"
        in out
    )

    org = Organization.objects.filter(organization_id="ch.geodienste-lu").first()
    assert org.name_de == "geodienste Luzern"
    assert org.name_en == "geodienste Lucerne"
    assert org.name_fr == "geodienste Lucerne"
    assert org.name_it == "geodienste Lucerna"
    assert org.name_rm == "geodienste Lucerna"
    assert org.acronym_de == "LU"
    assert org.acronym_fr == "LU"
    assert org.acronym_en == "LU"
    assert org.acronym_it == "LU"
    assert org.acronym_rm == "LU"
    assert org.data_source == Organization.DataSource.GEODIENSTE
    assert org.data_source_ids == ["LU"]

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.geodienste-lu already exists" in out


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_updates_cantonal_organization(mock, client, db):
    org = Organization(
        organization_id="ch.geodienste-lu",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DataSource.GEODIENSTE,
        data_source_ids=["LU"],
    )
    org.save()

    mock.side_effect = api_response(
        {"services": [{"base_topic": "av", "canton": "LU", "broker": None}]}
    )

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.geodienste-lu already exists" in out
    assert "Organization ch.geodienste-lu updated" in out

    org.refresh_from_db()
    assert org.name_de == "geodienste Luzern"
    assert org.name_en == "geodienste Lucerne"
    assert org.name_fr == "geodienste Lucerne"
    assert org.name_it == "geodienste Lucerna"
    assert org.name_rm == "geodienste Lucerna"
    assert org.acronym_de == "LU"
    assert org.acronym_fr == "LU"
    assert org.acronym_en == "LU"
    assert org.acronym_it == "LU"
    assert org.acronym_rm == "LU"
    assert org.data_source == Organization.DataSource.GEODIENSTE
    assert org.data_source_ids == ["LU"]

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.geodienste-lu already exists" in out


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_broker_organization(mock, client, db):
    mock.side_effect = api_response(
        {"services": [{"canton": "Broker", "broker": "BFE", "base_topic": "av"}]}
    )

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.bfe does not exist yet, creating a new one" in out

    org = Organization.objects.filter(organization_id="ch.bfe").first()
    assert org.name_de == "BFE"
    assert org.name_en == "BFE"
    assert org.name_fr == "BFE"
    assert org.name_it == "BFE"
    assert org.name_rm == "BFE"
    assert org.acronym_de == "BFE"
    assert org.acronym_fr == "BFE"
    assert org.acronym_en == "BFE"
    assert org.acronym_it == "BFE"
    assert org.acronym_rm == "BFE"
    assert org.data_source == Organization.DataSource.GEODIENSTE
    assert org.data_source_ids == ["BFE"]


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_updates_broker_organization(mock, client, db):
    org = Organization(
        organization_id="ch.bfe",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DataSource.GEODIENSTE,
        data_source_ids=["BFE"],
    )
    org.save()

    mock.side_effect = api_response(
        {"services": [{"base_topic": "av", "canton": None, "broker": "BFE"}]}
    )

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.bfe already exists" in out
    assert "Organization ch.bfe updated" in out

    org.refresh_from_db()
    assert org.name_de == "BFE"
    assert org.name_en == "BFE"
    assert org.name_fr == "BFE"
    assert org.name_it == "BFE"
    assert org.name_rm == "BFE"
    assert org.acronym_de == "BFE"
    assert org.acronym_fr == "BFE"
    assert org.acronym_en == "BFE"
    assert org.acronym_it == "BFE"
    assert org.acronym_rm == "BFE"
    assert org.data_source == Organization.DataSource.GEODIENSTE
    assert org.data_source_ids == ["BFE"]

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.bfe already exists" in out


@patch("organization.models.Client")
def test_command_creates_organization_from_file(client, db, tmp_path):
    for language in ("de", "fr", "it"):
        file = tmp_path / f"services_{language}.json"
        file.write_text(
            dumps({"services": [{"base_topic": "av", "canton": "Broker", "broker": "BFE"}]})
        )

    for language in ("de", "fr", "it", "en"):
        file = tmp_path / f"viewer_config_{language}.json"
        file.write_text(dumps({}))

    out = StringIO()
    call_command(
        "import_geodienste",
        organizations=True,
        directory=tmp_path,
        verbosity=2,
        stdout=out,
    )
    out = out.getvalue()

    assert "Organization with organization_id ch.bfe does not exist yet, creating a new one" in out


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_uses_organization_mapping(mock, client, db):
    org_1 = Organization(
        organization_id="ch.geodienste-lu-new",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DataSource.GEODIENSTE,
        data_source_ids=["LU"],
    )
    org_1.save()
    org_2 = Organization(
        organization_id="ch.geodienste-lu",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DataSource.GEODIENSTE,
        data_source_ids=["LU"],
    )
    org_2.save()

    mock.side_effect = api_response(
        {"services": [{"base_topic": "av", "canton": "LU", "broker": None}]}
    )

    # ---------
    # No update
    # ---------
    mapping = OrganizationMapping(
        provider_id_prefix="LU", organization_id="ch.geodienste-lu-new", update=False
    )
    mapping.save()

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id LU: ch.geodienste-lu-new" in out
    assert "Organization ch.geodienste-lu-new updated" not in out

    org_1.refresh_from_db()
    assert org_1.organization_id == "ch.geodienste-lu-new"
    assert org_1.name_de == "x"
    assert org_1.data_source_ids == ["LU"]

    org_2.refresh_from_db()
    assert org_2.data_source_ids == []

    # ---------
    # Update
    # ---------
    mapping.update = True
    mapping.save()

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id LU: ch.geodienste-lu-new" in out
    assert "Organization ch.geodienste-lu-new updated" in out

    org_1.refresh_from_db()
    assert org_1.organization_id == "ch.geodienste-lu-new"
    assert org_1.name_de == "geodienste Luzern"
    assert org_1.name_en == "geodienste Lucerne"
    assert org_1.name_fr == "geodienste Lucerne"
    assert org_1.name_it == "geodienste Lucerna"
    assert org_1.name_rm == "geodienste Lucerna"
    assert org_1.acronym_de == "LU"
    assert org_1.acronym_fr == "LU"
    assert org_1.acronym_en == "LU"
    assert org_1.acronym_it == "LU"
    assert org_1.acronym_rm == "LU"
    assert org_1.data_source == Organization.DataSource.GEODIENSTE
    assert org_1.data_source_ids == ["LU"]


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_cleans_organizations(mock, client, db):
    Organization(
        organization_id="obsolete",
        name_de="obsolete",
        name_en="obsolete",
        name_fr="obsolete",
        acronym_de="obsolete",
        acronym_fr="obsolete",
        acronym_en="obsolete",
        data_source=Organization.DataSource.GEODIENSTE,
        data_source_ids=[],
    ).save()
    Organization(
        organization_id="removed",
        name_de="removed",
        name_en="removed",
        name_fr="removed",
        acronym_de="removed",
        acronym_fr="removed",
        acronym_en="removed",
        data_source=Organization.DataSource.GEODIENSTE,
        data_source_ids=["removed"],
    ).save()

    mock.side_effect = api_response(
        {"services": [{"canton": "LU", "broker": None, "base_topic": "av"}]}
    )

    # --------
    # No clean
    # --------
    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removed data_source_ids (organization) found: removed" in out
    assert "Obsolete organizations found: obsolete" in out

    assert Organization.objects.filter(organization_id="obsolete").first()
    assert Organization.objects.filter(organization_id="removed").first()

    # --------
    # Clean
    # --------
    out = StringIO()
    call_command("import_geodienste", organizations=True, clean=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removing obsolete data_source_id (organization) removed" in out
    assert "Removing obsolete organization obsolete" in out
    assert "Removing obsolete organization removed" in out

    assert not Organization.objects.filter(organization_id="obsolete").first()
    assert not Organization.objects.filter(organization_id="removed").first()


# --------------------------------------------------------------------------------------------------
# Contacts
# --------------------------------------------------------------------------------------------------
@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_skips_aggregate_contact_if_no_org(mock, client, db):
    mock.side_effect = api_response(
        {
            "services": [
                {
                    "canton": "LU",
                    "broker": None,
                    "base_topic": "av",
                    "contact_geo": None,
                    "contact_specialist_department": None,
                },
            ]
        }
    )

    out = StringIO()
    call_command("import_geodienste", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.kgk does not exist, skipping" in out


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_aggregate_contact(mock, client, db):
    mock.side_effect = api_response(
        {
            "services": [
                {
                    "canton": "LU",
                    "broker": None,
                    "base_topic": "av",
                    "contact_geo": None,
                    "contact_specialist_department": None,
                },
            ]
        }
    )

    org = Organization(
        organization_id="ch.kgk",
        name_de="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_fr="Conférence des services cantonaux de la Géoinformation et du Cadastre",
        name_en="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_it="Conferenza dei servizi cantonali per la Geoinformazione e del Catasto",
        name_rm="Conferenza dals posts chantunals da Geoinfurmaziun e Cataster",
        acronym_de="KGK",
        acronym_fr="CGC",
        acronym_en="KGK",
        acronym_it="CGC",
        acronym_rm="CGC",
        data_source=Organization.DataSource.GEODIENSTE,
        data_source_ids=["KGK"],
    )
    org.save()

    out = StringIO()
    call_command("import_geodienste", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Contact KGK for organization ch.kgk does not exist yet, creating a new one" in out

    contact = org.contact_set.get()
    assert contact.data_source == Contact.DataSource.GEODIENSTE
    assert contact.data_source_ids == ["KGK"]
    assert contact.name_de == "Geschäftsstelle KGK-CGC"
    assert contact.name_fr == "Centre opérationnel KGK-CGC"
    assert contact.name_en == ""
    assert contact.name_it == "Direzione operativa KGK-CGC"
    assert contact.name_rm == ""
    assert contact.email == "geodienste@kgk-cgc.ch"
    assert contact.phone == "+41 31 300 09 20"
    assert contact.address_delivery_point == "Haus der Kantone, Speichergasse 6, Postfach"
    assert contact.address_postal_code == "3001"
    assert contact.address_city == "Bern"
    assert contact.address_country == "CH"
    assert contact.url_de == "https://kgk-cgc.ch/"
    assert contact.url_fr == "https://kgk-cgc.ch/fr"
    assert contact.url_en == ""
    assert contact.url_it == "https://kgk-cgc.ch/it"
    assert contact.url_rm == ""
    assert contact.legacy_contact == (
        "Geschäftsstelle KGK-CGC\n"
        "Haus der Kantone\n"
        "Speichergasse 6\n"
        "Postfach\n"
        "CH-3001 Bern\n"
        "Tel. +41 31 300 09 20\n"
        "geodienste@kgk-cgc.ch\n"
    )

    out = StringIO()
    call_command("import_geodienste", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Contact KGK for organization ch.kgk already exists" in out


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_updates_aggregate_contact(mock, client, db):
    mock.side_effect = api_response(
        {
            "services": [
                {
                    "canton": "LU",
                    "broker": None,
                    "base_topic": "av",
                    "contact_geo": None,
                    "contact_specialist_department": None,
                },
            ]
        }
    )

    org = Organization(
        organization_id="ch.kgk",
        name_de="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_fr="Conférence des services cantonaux de la Géoinformation et du Cadastre",
        name_en="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_it="Conferenza dei servizi cantonali per la Geoinformazione e del Catasto",
        name_rm="Conferenza dals posts chantunals da Geoinfurmaziun e Cataster",
        acronym_de="KGK",
        acronym_fr="CGC",
        acronym_en="KGK",
        acronym_it="CGC",
        acronym_rm="CGC",
        data_source=Organization.DataSource.GEODIENSTE,
        data_source_ids=["KGK"],
    )
    org.save()

    contact = Contact(
        organization=org,
        data_source=Organization.DataSource.GEODIENSTE,
        data_source_ids=["KGK"],
    )
    contact.save()

    out = StringIO()
    call_command("import_geodienste", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Contact KGK for organization ch.kgk already exists" in out
    assert "Contact KGK for organization ch.kgk updated" in out

    contact.refresh_from_db()
    assert contact.data_source == Contact.DataSource.GEODIENSTE
    assert contact.data_source_ids == ["KGK"]
    assert contact.name_de == "Geschäftsstelle KGK-CGC"
    assert contact.name_fr == "Centre opérationnel KGK-CGC"
    assert contact.name_en == ""
    assert contact.name_it == "Direzione operativa KGK-CGC"
    assert contact.name_rm == ""
    assert contact.email == "geodienste@kgk-cgc.ch"
    assert contact.phone == "+41 31 300 09 20"
    assert contact.address_delivery_point == "Haus der Kantone, Speichergasse 6, Postfach"
    assert contact.address_postal_code == "3001"
    assert contact.address_city == "Bern"
    assert contact.address_country == "CH"
    assert contact.url_de == "https://kgk-cgc.ch/"
    assert contact.url_fr == "https://kgk-cgc.ch/fr"
    assert contact.url_en == ""
    assert contact.url_it == "https://kgk-cgc.ch/it"
    assert contact.url_rm == ""
    assert contact.legacy_contact == (
        "Geschäftsstelle KGK-CGC\n"
        "Haus der Kantone\n"
        "Speichergasse 6\n"
        "Postfach\n"
        "CH-3001 Bern\n"
        "Tel. +41 31 300 09 20\n"
        "geodienste@kgk-cgc.ch\n"
    )

    out = StringIO()
    call_command("import_geodienste", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Contact KGK for organization ch.kgk updated" not in out


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_uses_aggregate_contact_mapping(mock, client, db):
    mock.side_effect = api_response(
        {
            "services": [
                {
                    "canton": "LU",
                    "broker": None,
                    "base_topic": "av",
                    "contact_geo": None,
                    "contact_specialist_department": None,
                },
            ]
        }
    )

    org = Organization(
        organization_id="ch.kgk-cgc",
        name_de="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_fr="Conférence des services cantonaux de la Géoinformation et du Cadastre",
        name_en="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_it="Conferenza dei servizi cantonali per la Geoinformazione e del Catasto",
        name_rm="Conferenza dals posts chantunals da Geoinfurmaziun e Cataster",
        acronym_de="KGK",
        acronym_fr="CGC",
        acronym_en="KGK",
        acronym_it="CGC",
        acronym_rm="CGC",
        data_source=Organization.DataSource.USER_INPUT,
        data_source_ids=[],
    )
    org.save()

    mapping = OrganizationMapping(
        provider_id_prefix="KGK", organization_id="ch.kgk-cgc", update=False
    )
    mapping.save()

    # ---------
    # Create
    # ---------
    out = StringIO()
    call_command("import_geodienste", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id KGK: ch.kgk-cgc" in out
    assert "Contact KGK for organization ch.kgk-cgc does not exist yet, creating a new one" in out

    contact = org.contact_set.get()
    assert contact.data_source == Contact.DataSource.GEODIENSTE
    assert contact.data_source_ids == ["KGK"]
    assert contact.name_de == "Geschäftsstelle KGK-CGC"
    assert contact.name_fr == "Centre opérationnel KGK-CGC"
    assert contact.name_en == ""
    assert contact.name_it == "Direzione operativa KGK-CGC"
    assert contact.name_rm == ""
    assert contact.email == "geodienste@kgk-cgc.ch"
    assert contact.phone == "+41 31 300 09 20"
    assert contact.address_delivery_point == "Haus der Kantone, Speichergasse 6, Postfach"
    assert contact.address_postal_code == "3001"
    assert contact.address_city == "Bern"
    assert contact.address_country == "CH"
    assert contact.url_de == "https://kgk-cgc.ch/"
    assert contact.url_fr == "https://kgk-cgc.ch/fr"
    assert contact.url_en == ""
    assert contact.url_it == "https://kgk-cgc.ch/it"
    assert contact.url_rm == ""
    assert contact.legacy_contact == (
        "Geschäftsstelle KGK-CGC\n"
        "Haus der Kantone\n"
        "Speichergasse 6\n"
        "Postfach\n"
        "CH-3001 Bern\n"
        "Tel. +41 31 300 09 20\n"
        "geodienste@kgk-cgc.ch\n"
    )

    # ---------
    # No update
    # ---------
    contact.name_de = "X"
    contact.save()

    out = StringIO()
    call_command("import_geodienste", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id KGK: ch.kgk-cgc" in out
    assert "Contact KGK for organization ch.kgk-cgc already exists" in out
    assert "Contact KGK for organization ch.kgk-cgc updated" not in out

    contact.refresh_from_db()
    assert contact.name_de == "X"

    # ---------
    # Update
    # ---------
    mapping.update = True
    mapping.save()

    out = StringIO()
    call_command("import_geodienste", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id KGK: ch.kgk-cgc" in out
    assert "Contact KGK for organization ch.kgk-cgc already exists" in out
    assert "Contact KGK for organization ch.kgk-cgc updated" in out

    contact.refresh_from_db()
    assert contact.name_de == "Geschäftsstelle KGK-CGC"


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_updates_cleans_contact(mock, client, db):
    org = Organization(
        organization_id="ch.geodienste-lu",
        name_de="geodienste Luzern",
        name_en="geodienste Lucerne",
        name_fr="geodienste Lucerne",
        name_it="geodienste Lucerna",
        name_rm="geodienste Lucerna",
        acronym_de="LU",
        acronym_fr="LU",
        acronym_en="LU",
        acronym_it="LU",
        acronym_rm="LU",
        data_source=Organization.DataSource.GEODIENSTE,
    )
    org.save()
    Contact(
        organization=org,
        data_source=Contact.DataSource.GEODIENSTE,
        data_source_ids=[],
        legacy_contact="obsolete",
        name_en="obsolete",
    ).save()
    Contact(
        organization=org,
        data_source=Contact.DataSource.GEODIENSTE,
        data_source_ids=["removed"],
        legacy_contact="removed",
        name_en="removed",
    ).save()
    Contact(organization=org, data_source=Contact.DataSource.GEOCAT, legacy_contact="geocat").save()

    # --------------
    # Create
    # --------------
    mock.side_effect = api_response(
        {
            "services": [
                {
                    "canton": "LU",
                    "broker": None,
                    "base_topic": "av",
                    "contact_geo": "Foo",
                    "contact_specialist_department": "Bar",
                },
                {
                    "canton": "LU",
                    "broker": None,
                    "base_topic": "gefahrenkarten",
                    "contact_geo": "Foo",
                    "contact_specialist_department": "Baz",
                },
                {
                    "canton": None,
                    "broker": "missing",
                    "base_topic": "missing",
                    "contact_geo": "Qux",
                    "contact_specialist_department": "Quz",
                },
            ]
        }
    )

    out = StringIO()
    call_command("import_geodienste", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Contact LU for organization ch.geodienste-lu does not exist yet, creating" in out
    assert "Contact LU.av for organization ch.geodienste-lu does not exist yet, creating" in out
    assert (
        "Contact LU.gefahrenkarten for organization ch.geodienste-lu does not exist yet, creating"
        in out
    )
    assert "Contact LU for organization ch.geodienste-lu already exists" in out
    assert "Organization with organization_id ch.missing does not exist, skipping" in out

    assert "Removed data_source_ids (contact) found: removed" in out
    assert "Obsolete contacts found: ch.geodienste-lu (obsolete)" in out

    assert Contact.objects.count() == 6
    assert {
        (tuple(contact.data_source_ids), contact.legacy_contact)
        for contact in org.contact_set.all()
    } == {
        ((), "obsolete"),
        (("removed",), "removed"),
        ((), "geocat"),
        (("LU",), "Foo"),
        (("LU.av",), "Bar"),
        (("LU.gefahrenkarten",), "Baz"),
    }

    # --------------
    # Update
    # --------------
    mock.side_effect = api_response(
        {
            "services": [
                {
                    "canton": "LU",
                    "broker": None,
                    "base_topic": "av",
                    "contact_geo": "Foobar",
                    "contact_specialist_department": "Quux",
                }
            ]
        }
    )

    out = StringIO()
    call_command("import_geodienste", contacts=True, clean=False, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Contact LU for organization ch.geodienste-lu already exists" in out
    assert "Contact LU for organization ch.geodienste-lu updated" in out
    assert "Contact LU.av for organization ch.geodienste-lu already exists" in out
    assert "Contact LU.av for organization ch.geodienste-lu updated" in out
    assert "Removed data_source_ids (contact) found: LU.gefahrenkarten, removed" in out
    assert "Obsolete contacts found: ch.geodienste-lu (obsolete)" in out

    assert Contact.objects.count() == 6
    assert {
        (tuple(contact.data_source_ids), contact.legacy_contact)
        for contact in org.contact_set.all()
    } == {
        ((), "obsolete"),
        (("removed",), "removed"),
        ((), "geocat"),
        (("LU",), "Foobar"),
        (("LU.av",), "Quux"),
        (("LU.gefahrenkarten",), "Baz"),
    }

    # --------------
    # Clean
    # --------------

    out = StringIO()
    call_command("import_geodienste", contacts=True, clean=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Contact LU for organization ch.geodienste-lu already exists" in out
    assert "Contact LU.av for organization ch.geodienste-lu already exists" in out
    assert "Removing obsolete data_source_id (contact) removed" in out
    assert "Removing obsolete data_source_id (contact) LU.gefahrenkarten" in out
    assert "Removing obsolete contact ch.geodienste-lu (obsolete)" in out
    assert "Removing obsolete contact ch.geodienste-lu (removed)" in out
    assert "Removing obsolete contact ch.geodienste-lu (None)" in out

    assert Contact.objects.count() == 3
    assert {
        (tuple(contact.data_source_ids), contact.legacy_contact)
        for contact in org.contact_set.all()
    } == {((), "geocat"), (("LU",), "Foobar"), (("LU.av",), "Quux")}


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_organization_mapping_for_contact(mock, client, db):
    org = Organization(
        organization_id="ch.geodienste-lu",
        name_de="geodienste Luzern",
        name_en="geodienste Lucerne",
        name_fr="geodienste Lucerne",
        name_it="geodienste Lucerna",
        name_rm="geodienste Lucerna",
        acronym_de="LU",
        acronym_fr="LU",
        acronym_en="LU",
        acronym_it="LU",
        acronym_rm="LU",
        data_source=Organization.DataSource.GEODIENSTE,
    )
    org.save()

    OrganizationMapping(
        provider_id_prefix="LU", organization_id="ch.geodienste-lu", update=True
    ).save()

    mock.side_effect = api_response(
        {
            "services": [
                {
                    "canton": "LU",
                    "broker": None,
                    "base_topic": "av",
                    "contact_geo": "Foo",
                    "contact_specialist_department": None,
                }
            ]
        }
    )

    out = StringIO()
    call_command("import_geodienste", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id LU: ch.geodienste-lu" in out
    assert "Contact LU for organization ch.geodienste-lu does not exist yet" in out

    assert Contact.objects.count() == 1
    assert {
        (tuple(contact.data_source_ids), contact.legacy_contact)
        for contact in org.contact_set.all()
    } == {(("LU",), "Foo")}


# --------------------------------------------------------------------------------------------------
# Datasets
# --------------------------------------------------------------------------------------------------
@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_datasets(mock, client, db):  # noqa: PLR0915
    org = Organization(
        organization_id="ch.kgk",
        name_de="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_fr="Conférence des services cantonaux de la Géoinformation et du Cadastre",
        name_en="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_it="Conferenza dei servizi cantonali per la Geoinformazione e del Catasto",
        name_rm="Conferenza dals posts chantunals da Geoinfurmaziun e Cataster",
        acronym_de="KGK",
        acronym_fr="CGC",
        acronym_en="KGK",
        acronym_it="CGC",
        acronym_rm="CGC",
    )
    org.save()

    contact = Contact(
        organization=org,
        email="geodienste@kgk-cgc.ch",
        phone="+41 31 300 09 20",
        address_delivery_point="Haus der Kantone, Speichergasse 6, Postfach",
        address_postal_code="3001",
        address_city="Bern",
        address_country="CH",
        url_de="https://kgk-cgc.ch/",
        url_fr="https://kgk-cgc.ch/fr",
        url_it="https://kgk-cgc.ch/it",
    )

    contact.save()

    meta_data = {
        "dataset_url": "https://www.geocat.ch/geonetwork/srv/ita/catalog.search#/metadata/d929eef4-791d-4728-9d56-226b6952cf1f"
    }
    mock.side_effect = api_response(
        {
            "de": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title DE",
                        "abstract": "Abstract DE",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "fr": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title FR",
                        "abstract": "Abstract FR",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "it": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title IT",
                        "abstract": "Abstract IT",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
        }
    )

    # ------
    # Create
    # ------
    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataset with dataset_id ch.kgk.av does not exist yet, creating a new one" in out
    assert (
        "Dataset with dataset_id ch.geodienste-lu.av does not exist yet, creating a new one" in out
    )
    assert "Adding relationship 'ch.geodienste-lu.av is a part of ch.kgk.av'" in out

    assert Dataset.objects.count() == 2

    aggregate = Dataset.objects.get(dataset_id="ch.kgk.av")
    assert aggregate.data_source == Dataset.DataSource.GEODIENSTE
    assert aggregate.data_source_ids == ["KGK.av"]
    assert aggregate.description_de == "Abstract DE"
    assert aggregate.description_en == "Abstract DE"
    assert aggregate.description_fr == "Abstract FR"
    assert aggregate.description_it == "Abstract IT"
    assert aggregate.description_rm is None
    assert aggregate.geocat_id == "d929eef4-791d-4728-9d56-226b6952cf1f"
    assert aggregate.title_short_de == "Title DE"
    assert aggregate.title_short_en == "Title DE"
    assert aggregate.title_short_fr == "Title FR"
    assert aggregate.title_short_it == "Title IT"
    assert aggregate.title_short_rm is None
    assert (
        aggregate.legacy_part_info_url_de
        == "https://geodienste.ch/services/av?locale=de#info_cantons"
    )
    assert (
        aggregate.legacy_part_info_url_fr
        == "https://geodienste.ch/services/av?locale=fr#info_cantons"
    )
    assert (
        aggregate.legacy_part_info_url_it
        == "https://geodienste.ch/services/av?locale=it#info_cantons"
    )
    assert aggregate.legacy_contacts == [
        {
            "role": "custodian",
            "org_name": "Konferenz der kantonalen Geoinformations- und Katasterstellen",
            "org_name_de": "Konferenz der kantonalen Geoinformations- und Katasterstellen",
            "org_name_en": "Konferenz der kantonalen Geoinformations- und Katasterstellen",
            "org_name_fr": "Conférence des services cantonaux de la Géoinformation et du Cadastre",
            "org_name_it": "Conferenza dei servizi cantonali per la Geoinformazione e del Catasto",
            "org_name_rm": "Conferenza dals posts chantunals da Geoinfurmaziun e Cataster",
            "org_acronym": "KGK",
            "org_acronym_de": "KGK",
            "org_acronym_fr": "CGC",
            "org_acronym_en": "KGK",
            "org_acronym_it": "CGC",
            "org_acronym_rm": "CGC",
            "contact_voice": "+41 31 300 09 20",
            "contact_city": "Bern",
            "contact_postal_code": "3001",
            "contact_country": "CH",
            "contact_electronic_mail_addresses": ["geodienste@kgk-cgc.ch"],
            "contact_delivery_point": "Haus der Kantone, Speichergasse 6, Postfach",
            "online_resources": [
                {
                    "url": "https://kgk-cgc.ch/",
                    "url_de": "https://kgk-cgc.ch/",
                    "url_fr": "https://kgk-cgc.ch/fr",
                    "url_en": None,
                    "url_it": "https://kgk-cgc.ch/it",
                    "url_rm": None,
                }
            ],
        }
    ]

    part = Dataset.objects.get(dataset_id="ch.geodienste-lu.av")
    assert part.data_source == Dataset.DataSource.GEODIENSTE
    assert part.data_source_ids == ["LU.av"]
    assert part.description_de == "Abstract DE"
    assert part.description_en == "Abstract DE"
    assert part.description_fr == "Abstract FR"
    assert part.description_it == "Abstract IT"
    assert part.description_rm is None
    assert part.geocat_id is None
    assert part.title_short_de == "Title DE"
    assert part.title_short_en == "Title DE"
    assert part.title_short_fr == "Title FR"
    assert part.title_short_it == "Title IT"
    assert part.title_short_rm is None

    assert aggregate.related_datasets(DatasetToDataset.Role.PART).first() == part

    # ------
    # Re-Run
    # ------
    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataset with dataset_id ch.kgk.av already exists" in out
    assert "Dataset with dataset_id ch.geodienste-lu.av already exists" in out


@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_updates_datasets(mock, db):
    aggregate = Dataset(
        dataset_id="ch.kgk.av",
        data_source=Dataset.DataSource.GEODIENSTE,
        data_source_ids=["KGK.av"],
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="Abstract FR",
        description_it="Abstract IT",
        description_rm=None,
        geocat_id="d929eef4-791d-4728-9d56-226b6952cf1f",
        title_short_de="Title DE",
        title_short_en="",
        title_short_fr="Title FR",
        title_short_it="Title IT",
        title_short_rm=None,
    )
    aggregate.save()

    part = Dataset(
        dataset_id="ch.geodienste-lu.av",
        data_source=Dataset.DataSource.GEODIENSTE,
        data_source_ids=["LU.av"],
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="",
        description_it="Abstract IT",
        description_rm=None,
        geocat_id=None,
        title_short_de="Title DE",
        title_short_en="Title DE",
        title_short_fr="Title FR",
        title_short_it="Title IT",
        title_short_rm=None,
    )
    part.save()

    meta_data = {
        "dataset_url": "https://www.geocat.ch/geonetwork/srv/ita/catalog.search#/metadata/d929eef4-791d-4728-9d56-226b6952cf1f"
    }
    mock.side_effect = api_response(
        {
            "de": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title DE",
                        "abstract": "Abstract DE",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "fr": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title FR",
                        "abstract": "Abstract FR",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "it": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title IT",
                        "abstract": "Abstract IT",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
        }
    )

    # ------
    # Create
    # ------
    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataset with dataset_id ch.kgk.av already exists" in out
    assert "Dataset with dataset_id ch.geodienste-lu.av already exists" in out
    assert "Dataset with dataset_id ch.kgk.av changed, updating" in out
    assert "Dataset with dataset_id ch.geodienste-lu.av changed, updating" in out
    assert "Adding relationship 'ch.geodienste-lu.av is a part of ch.kgk.av'" in out

    aggregate.refresh_from_db()
    assert aggregate.data_source == Dataset.DataSource.GEODIENSTE
    assert aggregate.data_source_ids == ["KGK.av"]
    assert aggregate.description_de == "Abstract DE"
    assert aggregate.description_en == "Abstract DE"
    assert aggregate.description_fr == "Abstract FR"
    assert aggregate.description_it == "Abstract IT"
    assert aggregate.description_rm is None
    assert aggregate.geocat_id == "d929eef4-791d-4728-9d56-226b6952cf1f"
    assert aggregate.title_short_de == "Title DE"
    assert aggregate.title_short_en == "Title DE"
    assert aggregate.title_short_fr == "Title FR"
    assert aggregate.title_short_it == "Title IT"
    assert aggregate.title_short_rm is None

    part.refresh_from_db()
    assert part.data_source == Dataset.DataSource.GEODIENSTE
    assert part.data_source_ids == ["LU.av"]
    assert part.dataset_id == "ch.geodienste-lu.av"
    assert part.description_de == "Abstract DE"
    assert part.description_en == "Abstract DE"
    assert part.description_fr == "Abstract FR"
    assert part.description_it == "Abstract IT"
    assert part.description_rm is None
    assert part.geocat_id is None
    assert part.preferred_distribution_id is None
    assert part.title_short_de == "Title DE"
    assert part.title_short_en == "Title DE"
    assert part.title_short_fr == "Title FR"
    assert part.title_short_it == "Title IT"
    assert part.title_short_rm is None

    assert aggregate.related_datasets(DatasetToDataset.Role.PART).first() == part

    # ------
    # Re-Run
    # ------
    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "updating" not in out


@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_uses_dataset_mapping(mock, db):
    aggregate = Dataset(
        dataset_id="ch.kgk-cgc.av",
        data_source=Dataset.DataSource.USER_INPUT,
        data_source_ids=[],
        description_de="x",
        description_en="x",
        description_fr="x",
        description_it="x",
        description_rm="x",
        geocat_id="x",
        title_short_de="x",
        title_short_en="x",
        title_short_fr="x",
        title_short_it="x",
        title_short_rm="x",
    )
    aggregate.save()

    part = Dataset(
        dataset_id="ch.rawi.av",
        data_source=Dataset.DataSource.USER_INPUT,
        data_source_ids=[],
        description_de="x",
        description_en="x",
        description_fr="x",
        description_it="x",
        description_rm="x",
        geocat_id=None,
        title_short_de="x",
        title_short_en="x",
        title_short_fr="x",
        title_short_it="x",
        title_short_rm="x",
    )
    part.save()

    aggregate_mapping = DatasetMapping(
        dataset_id_prefix="ch.kgk.av", dataset_id="ch.kgk-cgc.av", update=False
    )
    aggregate_mapping.save()
    part_mapping = DatasetMapping(
        dataset_id_prefix="ch.geodienste-lu.av", dataset_id="ch.rawi.av", update=False
    )
    part_mapping.save()

    meta_data = {
        "dataset_url": "https://www.geocat.ch/geonetwork/srv/ita/catalog.search#/metadata/d929eef4-791d-4728-9d56-226b6952cf1f"
    }
    mock.side_effect = api_response(
        {
            "de": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title DE",
                        "abstract": "Abstract DE",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "fr": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title FR",
                        "abstract": "Abstract FR",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "it": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title IT",
                        "abstract": "Abstract IT",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
        }
    )

    # ---------
    # No update
    # ---------
    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataset mapping found for dataset_id ch.kgk.av: ch.kgk-cgc.av" in out
    assert "Dataset mapping found for dataset_id ch.geodienste-lu.av: ch.rawi.av" in out

    aggregate.refresh_from_db()
    assert aggregate.title_short_de == "x"

    part.refresh_from_db()
    assert aggregate.title_short_de == "x"

    # ---------
    # Update
    # ---------
    aggregate_mapping.update = True
    aggregate_mapping.save()
    part_mapping.update = True
    part_mapping.save()

    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataset mapping found for dataset_id ch.kgk.av: ch.kgk-cgc.av" in out
    assert "Dataset mapping found for dataset_id ch.geodienste-lu.av: ch.rawi.av" in out
    assert "Dataset with dataset_id ch.kgk.av changed, updating" in out
    assert "Dataset with dataset_id ch.geodienste-lu.av changed, updating" in out

    aggregate.refresh_from_db()
    assert aggregate.data_source == Dataset.DataSource.USER_INPUT
    assert aggregate.data_source_ids == []
    assert aggregate.title_short_de == "Title DE"

    part.refresh_from_db()
    assert part.data_source == Dataset.DataSource.USER_INPUT
    assert part.data_source_ids == []
    assert part.title_short_de == "Title DE"

    assert aggregate.related_datasets(DatasetToDataset.Role.PART).first() == part


@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_cleans_datasets(mock, db):
    Dataset(
        dataset_id="obsolete",
        data_source=Dataset.DataSource.GEODIENSTE,
        data_source_ids=[],
        description_de="Obsolete",
        description_en="Obsolete",
        description_fr="Obsolete",
        title_short_de="Obsolete",
        title_short_en="Obsolete",
        title_short_fr="Obsolete",
    ).save()
    Dataset(
        dataset_id="removed",
        data_source=Dataset.DataSource.GEODIENSTE,
        data_source_ids=["KGK.removed"],
        description_de="Removed",
        description_en="Removed",
        description_fr="Removed",
        title_short_de="Removed",
        title_short_en="Removed",
        title_short_fr="Removed",
    ).save()

    mock.side_effect = api_response(
        {
            "de": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title DE",
                        "abstract": "Abstract DE",
                        "meta_data": {},
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "fr": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title FR",
                        "abstract": "Abstract FR",
                        "meta_data": {},
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "it": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title IT",
                        "abstract": "Abstract IT",
                        "meta_data": {},
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
        }
    )

    # ---------
    # No clean
    # --------
    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removed data_source_ids (dataset) found: KGK.removed" in out
    assert "Obsolete datasets found: obsolete" in out

    assert Dataset.objects.count() == 4

    # ------
    # Clean
    # ------
    out = StringIO()
    call_command("import_geodienste", datasets=True, clean=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removing obsolete data_source_id (dataset) KGK.removed" in out
    assert "Removing obsolete dataset obsolete" in out
    assert "Removing obsolete dataset removed" in out

    assert Dataset.objects.count() == 2


# --------------------------------------------------------------------------------------------------
# Dataset Units
# --------------------------------------------------------------------------------------------------
@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_removes_dataset_unit(mock, client, db):
    meta_data = {
        "dataset_url": "https://www.geocat.ch/geonetwork/srv/ita/catalog.search#/metadata/d929eef4-791d-4728-9d56-226b6952cf1f"
    }
    mock.side_effect = api_response(
        {
            "de": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title DE",
                        "abstract": "Abstract DE",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "fr": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title FR",
                        "abstract": "Abstract FR",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "it": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title IT",
                        "abstract": "Abstract IT",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
        }
    )

    # ------
    # No org
    # ------
    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.kgk does not exist" in out
    assert "Organization with organization_id ch.geodienste-lu does not exist" in out

    # ------
    # Create
    # ------
    org_aggregate = Organization(
        organization_id="ch.kgk",
        name_de="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_fr="Conférence des services cantonaux de la Géoinformation et du Cadastre",
        name_en="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_it="Conferenza dei servizi cantonali per la Geoinformazione e del Catasto",
        name_rm="Conferenza dals posts chantunals da Geoinfurmaziun e Cataster",
        acronym_de="KGK",
        acronym_fr="CGC",
        acronym_en="KGK",
        acronym_it="CGC",
        acronym_rm="CGC",
        data_source=Organization.DataSource.GEODIENSTE,
        data_source_ids=["KGK"],
    )
    org_aggregate.save()

    org_part = Organization(
        organization_id="ch.geodienste-lu",
        name_de="Kanton Luzern",
        name_en="Canton of Lucerne",
        name_fr="Canton de Lucerne",
        name_it="Cantone di Lucerna",
        name_rm="Chantun Lucerna",
        acronym_de="LU",
        acronym_fr="LU",
        acronym_en="LU",
        acronym_it="LU",
        acronym_rm="LU",
        data_source=Organization.DataSource.GEODIENSTE,
    )
    org_part.save()

    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Creating dataset unit ch.kgk (default) as maintainer in ch.kgk.av" in out
    assert (
        "Creating dataset unit ch.geodienste-lu (default) as maintainer in ch.geodienste-lu.av"
        in out
    )

    dataset_unit = org_aggregate.unit_set.get().dataset_units.get()
    assert dataset_unit.role == DatasetToUnit.Role.MAINTAINER
    assert dataset_unit.dataset.dataset_id == "ch.kgk.av"

    dataset_unit = org_part.unit_set.get().dataset_units.get()
    assert dataset_unit.role == DatasetToUnit.Role.MAINTAINER
    assert dataset_unit.dataset.dataset_id == "ch.geodienste-lu.av"

    # ------
    # Rerun
    # ------
    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataset unit ch.kgk (default) as maintainer in ch.kgk.av already exists" in out
    assert (
        "Dataset unit ch.geodienste-lu (default) as maintainer in ch.geodienste-lu.av already "
        "exists" in out
    )

    # ------
    # Update
    # ------
    dataset = Dataset.objects.get(dataset_id="ch.geodienste-lu.av")
    unit = org_aggregate.unit_set.get()
    DatasetToUnit(dataset=dataset, unit=unit, role=DatasetToUnit.Role.MAINTAINER).save()
    DatasetToUnit(dataset=dataset, unit=unit, role=DatasetToUnit.Role.OWNER).save()

    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert (
        "Removing obsolete dataset unit ch.kgk (default) as maintainer in ch.geodienste-lu.av"
        in out
    )

    assert dataset.dataset_units.count() == 2


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_uses_org_mapping_for_dataset_unit(mock, client, db):
    org_aggregate = Organization(
        organization_id="ch.kgk-cgc",
        name_de="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_fr="Conférence des services cantonaux de la Géoinformation et du Cadastre",
        name_en="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_it="Conferenza dei servizi cantonali per la Geoinformazione e del Catasto",
        name_rm="Conferenza dals posts chantunals da Geoinfurmaziun e Cataster",
        acronym_de="KGK",
        acronym_fr="CGC",
        acronym_en="KGK",
        acronym_it="CGC",
        acronym_rm="CGC",
    )
    org_aggregate.save()

    org_part = Organization(
        organization_id="ch.rawi",
        name_de="Raum und Wirtschaft",
        name_en="Raum und Wirtschaft",
        name_fr="Raum und Wirtschaft",
        acronym_de="RAWI",
        acronym_fr="RAWI",
        acronym_en="RAWI",
    )
    org_part.save()

    meta_data = {
        "dataset_url": "https://www.geocat.ch/geonetwork/srv/ita/catalog.search#/metadata/d929eef4-791d-4728-9d56-226b6952cf1f"
    }
    mock.side_effect = api_response(
        {
            "de": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title DE",
                        "abstract": "Abstract DE",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "fr": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title FR",
                        "abstract": "Abstract FR",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "it": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title IT",
                        "abstract": "Abstract IT",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
        }
    )

    OrganizationMapping(provider_id_prefix="KGK", organization_id="ch.kgk-cgc").save()
    OrganizationMapping(provider_id_prefix="LU", organization_id="ch.rawi").save()

    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id KGK: ch.kgk-cgc" in out
    assert "Mapping found for provider_id LU: ch.rawi" in out
    assert "Creating dataset unit ch.kgk-cgc (default) as maintainer in ch.kgk.av" in out
    assert "Creating dataset unit ch.rawi (default) as maintainer in ch.geodienste-lu.av" in out

    dataset_unit = org_aggregate.unit_set.get().dataset_units.get()
    assert dataset_unit.role == DatasetToUnit.Role.MAINTAINER
    assert dataset_unit.dataset.dataset_id == "ch.kgk.av"

    dataset_unit = org_part.unit_set.get().dataset_units.get()
    assert dataset_unit.role == DatasetToUnit.Role.MAINTAINER
    assert dataset_unit.dataset.dataset_id == "ch.geodienste-lu.av"


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_uses_mapping_for_dataset_unit(mock, client, db):
    org_aggregate = Organization(
        organization_id="ch.kgk-cgc",
        name_de="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_fr="Conférence des services cantonaux de la Géoinformation et du Cadastre",
        name_en="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_it="Conferenza dei servizi cantonali per la Geoinformazione e del Catasto",
        name_rm="Conferenza dals posts chantunals da Geoinfurmaziun e Cataster",
        acronym_de="KGK",
        acronym_fr="CGC",
        acronym_en="KGK",
        acronym_it="CGC",
        acronym_rm="CGC",
    )
    org_aggregate.save()
    unit_aggregate = Unit(
        organization=org_aggregate, unit_id="aggregate", name_de="x", name_fr="x", name_en="x"
    )
    unit_aggregate.save()

    org_part = Organization(
        organization_id="ch.rawi",
        name_de="Raum und Wirtschaft",
        name_en="Raum und Wirtschaft",
        name_fr="Raum und Wirtschaft",
        acronym_de="RAWI",
        acronym_fr="RAWI",
        acronym_en="RAWI",
    )
    org_part.save()
    unit_part = Unit(organization=org_part, unit_id="part", name_de="x", name_fr="x", name_en="x")
    unit_part.save()

    meta_data = {
        "dataset_url": "https://www.geocat.ch/geonetwork/srv/ita/catalog.search#/metadata/d929eef4-791d-4728-9d56-226b6952cf1f"
    }
    mock.side_effect = api_response(
        {
            "de": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title DE",
                        "abstract": "Abstract DE",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "fr": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title FR",
                        "abstract": "Abstract FR",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "it": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title IT",
                        "abstract": "Abstract IT",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
        }
    )

    DatasetToUnitMapping(
        dataset_id_prefix="ch.kgk.av", organization_id="ch.kgk-cgc", unit_id="aggregate"
    ).save()
    DatasetToUnitMapping(
        dataset_id_prefix="ch.geodienste-lu.av", organization_id="ch.rawi", unit_id="part"
    ).save()

    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Unit mapping found for dataset_id ch.kgk.av: aggregate" in out
    assert "Unit mapping found for dataset_id ch.geodienste-lu.av: part" in out

    dataset_unit = unit_aggregate.dataset_units.get()
    assert dataset_unit.role == DatasetToUnit.Role.MAINTAINER
    assert dataset_unit.dataset.dataset_id == "ch.kgk.av"

    dataset_unit = unit_part.dataset_units.get()
    assert dataset_unit.role == DatasetToUnit.Role.MAINTAINER
    assert dataset_unit.dataset.dataset_id == "ch.geodienste-lu.av"


# --------------------------------------------------------------------------------------------------
# Dataset Contacts
# --------------------------------------------------------------------------------------------------
@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_updates_cleans_dataset_contacts(mock, client, db):
    org_aggregate = Organization(
        organization_id="ch.kgk",
        name_de="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_fr="Conférence des services cantonaux de la Géoinformation et du Cadastre",
        name_en="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_it="Conferenza dei servizi cantonali per la Geoinformazione e del Catasto",
        name_rm="Conferenza dals posts chantunals da Geoinfurmaziun e Cataster",
        acronym_de="KGK",
        acronym_fr="CGC",
        acronym_en="KGK",
        acronym_it="CGC",
        acronym_rm="CGC",
        data_source=Organization.DataSource.GEODIENSTE,
        data_source_ids=["KGK"],
    )
    org_aggregate.save()
    contact_aggregate = Contact(
        organization=org_aggregate,
        data_source=Contact.DataSource.GEODIENSTE,
        data_source_ids=["KGK"],
        name_en="kgk",
    )
    contact_aggregate.save()

    org_part = Organization(
        organization_id="ch.geodienste-lu",
        name_de="Kanton Luzern",
        name_en="Canton of Lucerne",
        name_fr="Canton de Lucerne",
        name_it="Cantone di Lucerna",
        name_rm="Chantun Lucerna",
        acronym_de="LU",
        acronym_fr="LU",
        acronym_en="LU",
        acronym_it="LU",
        acronym_rm="LU",
        data_source=Organization.DataSource.GEODIENSTE,
    )
    org_part.save()
    contact_part_org = Contact(
        organization=org_part,
        data_source=Contact.DataSource.GEODIENSTE,
        data_source_ids=["LU"],
        name_en="LU",
    )
    contact_part_org.save()
    contact_part_specialist = Contact(
        organization=org_part,
        data_source=Contact.DataSource.GEODIENSTE,
        data_source_ids=["LU.av"],
        name_en="LU.av",
    )
    contact_part_specialist.save()

    meta_data = {
        "dataset_url": "https://www.geocat.ch/geonetwork/srv/ita/catalog.search#/metadata/d929eef4-791d-4728-9d56-226b6952cf1f"
    }
    mock.side_effect = api_response(
        {
            "de": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title DE",
                        "abstract": "Abstract DE",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "fr": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title FR",
                        "abstract": "Abstract FR",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "it": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title IT",
                        "abstract": "Abstract IT",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
        }
    )

    # ------
    # Create
    # ------
    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Creating dataset contact ch.kgk (kgk) as custodian in ch.kgk.av" in out
    assert (
        "Creating dataset contact ch.geodienste-lu (LU.av) as owner in ch.geodienste-lu.av" in out
    )
    assert (
        "Creating dataset contact ch.geodienste-lu (LU) as custodian in ch.geodienste-lu.av" in out
    )

    dataset_contact = contact_aggregate.dataset_contacts.get()
    assert dataset_contact.role == DatasetToContact.Role.CUSTODIAN
    assert dataset_contact.dataset.dataset_id == "ch.kgk.av"

    dataset_contact = contact_part_org.dataset_contacts.get()
    assert dataset_contact.role == DatasetToContact.Role.CUSTODIAN
    assert dataset_contact.dataset.dataset_id == "ch.geodienste-lu.av"

    dataset_contact = contact_part_specialist.dataset_contacts.get()
    assert dataset_contact.role == DatasetToContact.Role.OWNER
    assert dataset_contact.dataset.dataset_id == "ch.geodienste-lu.av"

    # ------
    # Update
    # ------
    contact_aggregate.data_source_ids = []
    contact_aggregate.save()

    contact_aggregate_new = Contact(
        organization=org_aggregate,
        data_source=Contact.DataSource.GEODIENSTE,
        data_source_ids=["KGK"],
        name_en="kgk_new",
    )
    contact_aggregate_new.save()

    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removing obsolete dataset contact ch.kgk (kgk) as custodian in ch.kgk.av" in out
    assert "Creating dataset contact ch.kgk (kgk_new) as custodian in ch.kgk.av" in out
    assert (
        "Dataset contact ch.geodienste-lu (LU.av) as owner in ch.geodienste-lu.av already exists"
        in out
    )
    assert (
        "Dataset contact ch.geodienste-lu (LU) as custodian in ch.geodienste-lu.av already exists"
        in out
    )

    assert contact_aggregate.dataset_contacts.first() is None

    dataset_contact = contact_aggregate_new.dataset_contacts.get()
    assert dataset_contact.role == DatasetToContact.Role.CUSTODIAN
    assert dataset_contact.dataset.dataset_id == "ch.kgk.av"

    dataset_contact = contact_part_org.dataset_contacts.get()
    assert dataset_contact.role == DatasetToContact.Role.CUSTODIAN
    assert dataset_contact.dataset.dataset_id == "ch.geodienste-lu.av"

    dataset_contact = contact_part_specialist.dataset_contacts.get()
    assert dataset_contact.role == DatasetToContact.Role.OWNER
    assert dataset_contact.dataset.dataset_id == "ch.geodienste-lu.av"


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_uses_contact_mappings(mock, client, db):
    org_aggregate = Organization(
        organization_id="ch.kgk",
        name_de="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_fr="Conférence des services cantonaux de la Géoinformation et du Cadastre",
        name_en="Konferenz der kantonalen Geoinformations- und Katasterstellen",
        name_it="Conferenza dei servizi cantonali per la Geoinformazione e del Catasto",
        name_rm="Conferenza dals posts chantunals da Geoinfurmaziun e Cataster",
        acronym_de="KGK",
        acronym_fr="CGC",
        acronym_en="KGK",
        acronym_it="CGC",
        acronym_rm="CGC",
    )
    org_aggregate.save()
    contact_aggregate = Contact(
        organization=org_aggregate,
        data_source=Contact.DataSource.GEODIENSTE,
        name_en="KGK",
    )
    contact_aggregate.save()

    org_part = Organization(
        organization_id="ch.geodienste-lu",
        name_de="Kanton Luzern",
        name_en="Canton of Lucerne",
        name_fr="Canton de Lucerne",
        name_it="Cantone di Lucerna",
        name_rm="Chantun Lucerna",
        acronym_de="LU",
        acronym_fr="LU",
        acronym_en="LU",
        acronym_it="LU",
        acronym_rm="LU",
    )
    org_part.save()
    contact_part_org = Contact(
        organization=org_part,
        name_en="LU",
    )
    contact_part_org.save()
    contact_part_specialist = Contact(
        organization=org_part,
        name_en="LU.av",
    )
    contact_part_specialist.save()

    DatasetToContactMapping(
        dataset_id_prefix="ch.kgk.av",
        role=DatasetToContact.Role.CUSTODIAN,
        organization_id="ch.kgk",
        contact_name_en="KGK",
    ).save()
    DatasetToContactMapping(
        dataset_id_prefix="ch.geodienste-lu.av",
        role=DatasetToContact.Role.CUSTODIAN,
        organization_id="ch.geodienste-lu",
        contact_name_en="LU",
    ).save()
    DatasetToContactMapping(
        dataset_id_prefix="ch.geodienste-lu.av",
        role=DatasetToContact.Role.OWNER,
        organization_id="ch.geodienste-lu",
        contact_name_en="LU.av",
    ).save()

    meta_data = {
        "dataset_url": "https://www.geocat.ch/geonetwork/srv/ita/catalog.search#/metadata/d929eef4-791d-4728-9d56-226b6952cf1f"
    }
    mock.side_effect = api_response(
        {
            "de": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title DE",
                        "abstract": "Abstract DE",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "fr": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title FR",
                        "abstract": "Abstract FR",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
            "it": {
                "services": [
                    {
                        "canton": "LU",
                        "broker": None,
                        "base_topic": "av",
                        "topic_title": "Title IT",
                        "abstract": "Abstract IT",
                        "meta_data": meta_data,
                        "website": "https://geodienste.ch/services/av",
                    }
                ]
            },
        }
    )

    out = StringIO()
    call_command("import_geodienste", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Contact mapping found for dataset_id ch.kgk.av and role custodian: ch.kgk (KGK)" in out
    assert (
        "Contact mapping found for dataset_id ch.geodienste-lu.av and role owner: "
        "ch.geodienste-lu (LU.av)" in out
    )
    assert (
        "Contact mapping found for dataset_id ch.geodienste-lu.av and role custodian: "
        "ch.geodienste-lu (LU)" in out
    )
    assert "Creating dataset contact ch.kgk (KGK) as custodian in ch.kgk.av" in out
    assert (
        "Creating dataset contact ch.geodienste-lu (LU.av) as owner in ch.geodienste-lu.av" in out
    )
    assert (
        "Creating dataset contact ch.geodienste-lu (LU) as custodian in ch.geodienste-lu.av" in out
    )

    dataset_contact = contact_aggregate.dataset_contacts.get()
    assert dataset_contact.role == DatasetToContact.Role.CUSTODIAN
    assert dataset_contact.dataset.dataset_id == "ch.kgk.av"

    dataset_contact = contact_part_org.dataset_contacts.get()
    assert dataset_contact.role == DatasetToContact.Role.CUSTODIAN
    assert dataset_contact.dataset.dataset_id == "ch.geodienste-lu.av"

    dataset_contact = contact_part_specialist.dataset_contacts.get()
    assert dataset_contact.role == DatasetToContact.Role.OWNER
    assert dataset_contact.dataset.dataset_id == "ch.geodienste-lu.av"


# --------------------------------------------------------------------------------------------------
# Keywords
# --------------------------------------------------------------------------------------------------
@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
@patch("thesaurus.utils.get", name="rdf")
def test_command_creates_keywords(rdf, mock, client, db):
    aggregate_dataset = Dataset(
        dataset_id="ch.kgk.av",
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="Abstract FR",
        title_short_de="Title DE",
        title_short_en="Title EN",
        title_short_fr="Title FR",
    )
    aggregate_dataset.save()

    part_dataset = Dataset(
        dataset_id="ch.geodienste-lu.av",
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="Abstract FR",
        title_short_de="Title DE",
        title_short_en="Title EN",
        title_short_fr="Title FR",
    )
    part_dataset.save()

    mock.side_effect = api_response(
        {
            "services": [
                {
                    "canton": "LU",
                    "broker": None,
                    "base_topic": "av",
                    "keywords_gemet": "foo de",
                    "keywords_geocat": "bar de, baz de",
                }
            ]
        }
    )

    gemet_response = Mock()
    gemet_response.status_code = 200
    gemet_response.content = """<?xml version="1.0" encoding="UTF-8"?>
        <rdf:RDF
            xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:ns4="http://www.opengis.net/gml#"
            xmlns:skos="http://www.w3.org/2004/02/skos/core#"
            xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">

            <rdf:Description rdf:about="concept/1">
                <skos:prefLabel xml:lang="de">foo de</skos:prefLabel>
                <skos:prefLabel xml:lang="fr">foo fr</skos:prefLabel>
                <skos:prefLabel xml:lang="en">foo en</skos:prefLabel>
                <skos:prefLabel xml:lang="it">foo it</skos:prefLabel>
                <rdf:type rdf:resource="http://www.w3.org/2004/02/skos/core#Concept"/>
            </rdf:Description>
        </rdf:RDF>"""

    geocat_response = Mock()
    geocat_response.status_code = 200
    geocat_response.content = """<?xml version="1.0" encoding="UTF-8"?>
        <rdf:RDF
            xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:ns4="http://www.opengis.net/gml#"
            xmlns:skos="http://www.w3.org/2004/02/skos/core#"
            xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">

            <rdf:Description rdf:about="http://geocat.ch/concept#1">
                <skos:prefLabel xml:lang="de">bar de</skos:prefLabel>
                <skos:prefLabel xml:lang="fr">bar fr</skos:prefLabel>
                <skos:prefLabel xml:lang="en">bar en</skos:prefLabel>
                <skos:prefLabel xml:lang="it">bar it</skos:prefLabel>
                <skos:prefLabel xml:lang="rm">bar rm</skos:prefLabel>
                <rdf:type rdf:resource="http://www.w3.org/2004/02/skos/core#Concept"/>
            </rdf:Description>
        </rdf:RDF>"""

    # ------
    # Create
    # ------
    rdf.side_effect = [gemet_response, geocat_response]

    out = StringIO()
    call_command("import_geodienste", keywords=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Thesaurus geonetwork.thesaurus.external.theme.gemet created" in out
    assert "Thesaurus geonetwork.thesaurus.local.theme.geocat.ch created" in out
    assert "Loading lookup table / RDF from" in out
    assert "www.geocat.ch/geonetwork/srv/api/registries/vocabularies/external.theme.gemet" in out
    assert "www.geocat.ch/geonetwork/srv/api/registries/vocabularies/local.theme.geocat.ch" in out
    assert "Adding keyword concept/1" in out
    assert "Adding keyword http://geocat.ch/concept#1" in out
    assert "Keyword baz de not found in thesaurus ThesaurusLookup" in out

    assert {k.label_fr for k in aggregate_dataset.keywords.all()} == {"bar fr", "foo fr"}
    assert {k.label_fr for k in part_dataset.keywords.all()} == {"bar fr", "foo fr"}
    assert Thesaurus.objects.count() == 2

    gemet = Thesaurus.objects.get(thesaurus_id="geonetwork.thesaurus.external.theme.gemet")
    keyword = gemet.keyword_set.first()
    assert keyword.label_de == "foo de"
    assert keyword.label_fr == "foo fr"
    assert keyword.label_en == "foo en"
    assert keyword.label_it == "foo it"
    assert keyword.label_rm is None

    geocat = Thesaurus.objects.get(thesaurus_id="geonetwork.thesaurus.local.theme.geocat.ch")
    keyword = geocat.keyword_set.first()
    assert keyword.label_de == "bar de"
    assert keyword.label_fr == "bar fr"
    assert keyword.label_en == "bar en"
    assert keyword.label_it == "bar it"
    assert keyword.label_rm == "bar rm"

    # ------
    # Re-run
    # ------
    part_dataset.keywords.clear()

    rdf.side_effect = [gemet_response, geocat_response]

    out = StringIO()
    call_command("import_geodienste", keywords=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert {k.label_fr for k in aggregate_dataset.keywords.all()} == {"bar fr", "foo fr"}
    assert {k.label_fr for k in part_dataset.keywords.all()} == {"bar fr", "foo fr"}


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
@patch("thesaurus.utils.get", name="rdf")
def test_command_use_mapping_for_keywords(rdf, mock, client, db):
    aggregate_dataset = Dataset(
        dataset_id="ch.kgk-cgc.av",
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="Abstract FR",
        title_short_de="Title DE",
        title_short_en="Title EN",
        title_short_fr="Title FR",
    )
    aggregate_dataset.save()

    part_dataset = Dataset(
        dataset_id="ch.rawi.av",
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="Abstract FR",
        title_short_de="Title DE",
        title_short_en="Title EN",
        title_short_fr="Title FR",
    )
    part_dataset.save()

    aggregate_mapping = DatasetMapping(
        dataset_id_prefix="ch.kgk.av", dataset_id="ch.kgk-cgc.av", update=False
    )
    aggregate_mapping.save()

    part_mapping = DatasetMapping(
        dataset_id_prefix="ch.geodienste-lu.av", dataset_id="ch.rawi.av", update=False
    )
    part_mapping.save()

    mock.side_effect = api_response(
        {
            "services": [
                {
                    "canton": "LU",
                    "broker": None,
                    "base_topic": "av",
                    "keywords_gemet": "foo de",
                    "keywords_geocat": None,
                }
            ]
        }
    )

    gemet_response = Mock()
    gemet_response.status_code = 200
    gemet_response.content = """<?xml version="1.0" encoding="UTF-8"?>
        <rdf:RDF
            xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:ns4="http://www.opengis.net/gml#"
            xmlns:skos="http://www.w3.org/2004/02/skos/core#"
            xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">

            <rdf:Description rdf:about="concept/1">
                <skos:prefLabel xml:lang="de">foo de</skos:prefLabel>
                <skos:prefLabel xml:lang="fr">foo fr</skos:prefLabel>
                <skos:prefLabel xml:lang="en">foo en</skos:prefLabel>
                <skos:prefLabel xml:lang="it">foo it</skos:prefLabel>
                <rdf:type rdf:resource="http://www.w3.org/2004/02/skos/core#Concept"/>
            </rdf:Description>
        </rdf:RDF>"""

    geocat_response = Mock()
    geocat_response.status_code = 200
    geocat_response.content = """<?xml version="1.0" encoding="UTF-8"?>
        <rdf:RDF
            xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:ns4="http://www.opengis.net/gml#"
            xmlns:skos="http://www.w3.org/2004/02/skos/core#"
            xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
        </rdf:RDF>"""

    # ---------
    # No update
    # ---------
    rdf.side_effect = [gemet_response, geocat_response]

    out = StringIO()
    call_command("import_geodienste", keywords=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataset mapping found for dataset_id ch.kgk.av: ch.kgk-cgc.av" in out
    assert "Dataset mapping found for dataset_id ch.geodienste-lu.av: ch.rawi.av" in out

    assert aggregate_dataset.keywords.count() == 0
    assert part_dataset.keywords.count() == 0

    # ------
    # Re-run
    # ------
    aggregate_mapping.update = True
    aggregate_mapping.save()

    part_mapping.update = True
    part_mapping.save()

    rdf.side_effect = [gemet_response, geocat_response]

    out = StringIO()
    call_command("import_geodienste", keywords=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert aggregate_dataset.keywords.count() == 1
    assert part_dataset.keywords.count() == 1


# --------------------------------------------------------------------------------------------------
# Distributions
# --------------------------------------------------------------------------------------------------
@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_updates_distributions(mock, client, db):  # noqa: PLR0915
    out = StringIO()
    call_command("loaddata", "app/fixtures/dataservice.json", stdout=out)
    out = out.getvalue()
    assert "Installed" in out

    dataset = Dataset(
        dataset_id="ch.kgk.fixpunkte",
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="Abstract FR",
        title_short_de="Title DE",
        title_short_en="Title EN",
        title_short_fr="Title FR",
    )
    dataset.save()

    # ------
    # Create
    # ------
    mock.side_effect = api_response(
        services={
            "services": [
                {
                    "base_topic": "fixpunkte",
                    "canton": "lu",
                    "broker": None,
                }
            ]
        },
        config={
            "de": {
                "fixpunkte": {
                    "default": {
                        "layers": [{"name": "daten", "opacity": 0.9}],
                        "legend_layer": "daten",
                        "wms": "https://geodienste.ch/db/fixpunkte_0/deu",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita", "eng"],
                    "derivates": {},
                }
            },
            "fr": {
                "fixpunkte": {
                    "default": {
                        "layers": [{"name": "donnees", "opacity": 0.9}],
                        "legend_layer": "donnees",
                        "wms": "https://geodienste.ch/db/fixpunkte_0/fra",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita", "eng"],
                    "derivates": {},
                }
            },
            "it": {
                "fixpunkte": {
                    "default": {
                        "layers": [{"name": "dati", "opacity": 0.9}],
                        "legend_layer": "dati",
                        "wms": "https://geodienste.ch/db/fixpunkte_0/ita",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita", "eng"],
                    "derivates": {},
                }
            },
            "en": {
                "fixpunkte": {
                    "default": {
                        "layers": [{"name": "data", "opacity": 0.9}],
                        "legend_layer": "data",
                        "wms": "https://geodienste.ch/db/fixpunkte_0/eng",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita", "eng"],
                    "derivates": {},
                }
            },
        },
    )

    out = StringIO()
    call_command("import_geodienste", distributions=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert (
        "Dataservice with dataservice_id wms-geodienste-fixpunkte does not exist yet, creating"
        in out
    )
    assert (
        "Dataservice with dataservice_id wms-geodienste-fixpunkte-availability does not exist"
        in out
    )
    assert (
        "Distribution with distribution_id ch.kgk.fixpunkte:wms does not exist yet, creating" in out
    )
    assert (
        "Distribution with distribution_id ch.kgk.fixpunkte-availability:wms does not exist" in out
    )
    assert (
        "Setting ch.kgk.fixpunkte:wms as preferred distribution for dataset ch.kgk.fixpunkte" in out
    )

    dataservice_data = Dataservice.objects.get(dataservice_id="wms-geodienste-fixpunkte")
    assert dataservice_data.data_source == "geodienste"
    assert dataservice_data.default_language == "de"
    assert dataservice_data.languages == ["de", "fr", "it", "en"]
    assert dataservice_data.title == "WMS geodienste.ch fixpunkte"
    assert (
        dataservice_data.capabilities_url
        == "https://geodienste.ch/db/fixpunkte_0/{lang3}?SERVICE=WMS&REQUEST=GetCapabilities"
    )

    dataservice_availability = Dataservice.objects.get(
        dataservice_id="wms-geodienste-fixpunkte-availability"
    )
    assert dataservice_availability.data_source == "geodienste"
    assert dataservice_availability.default_language == "de"
    assert dataservice_availability.languages == ["de", "fr", "it", "en"]
    assert dataservice_availability.title == "WMS geodienste.ch fixpunkte (availability)"
    assert (
        dataservice_availability.capabilities_url
        == "https://geodienste.ch/db/availability/fixpunkte/portrayal/{lang3}?SERVICE=WMS&REQUEST=GetCapabilities"
    )

    distribution_data = ExternalWMSDistribution.objects.get(distribution_id="ch.kgk.fixpunkte:wms")
    assert distribution_data.data_source == "geodienste"
    assert distribution_data.title_de == "Title DE"
    assert distribution_data.title_en == "Title EN"
    assert distribution_data.title_fr == "Title FR"
    assert distribution_data.description_de == "Abstract DE"
    assert distribution_data.description_en == "Abstract EN"
    assert distribution_data.description_fr == "Abstract FR"
    assert distribution_data.wms_layer_name_de == "daten"
    assert distribution_data.wms_layer_name_fr == "donnees"
    assert distribution_data.wms_layer_name_it == "dati"
    assert distribution_data.wms_layer_name_en == "data"
    assert distribution_data.wms_layer_name_rm is None
    assert distribution_data.opacity == Decimal("0.90")
    assert distribution_data.meta_information is False
    assert distribution_data.dataservice == dataservice_data
    assert distribution_data.dataset == dataset

    distribution_availability = ExternalWMSDistribution.objects.get(
        distribution_id="ch.kgk.fixpunkte-availability:wms"
    )
    assert distribution_availability.data_source == "geodienste"
    assert distribution_availability.title_de == "Verfügbarkeit"
    assert distribution_availability.title_en == "Availability"
    assert distribution_availability.title_fr == "Disponibilité"
    assert distribution_availability.title_it == "Disponibilità"
    assert distribution_availability.description_de == "Kantonalen Verfügbarkeit der Daten."
    assert distribution_availability.description_en == "Availability of data at cantonal level."
    assert (
        distribution_availability.description_fr == "Disponibilité des données au niveau cantonal."
    )
    assert distribution_availability.description_it == "Disponibilità dei dati a livello cantonale."
    assert distribution_availability.wms_layer_name_de == "availability_cantons"
    assert distribution_availability.wms_layer_name_fr == "availability_cantons"
    assert distribution_availability.wms_layer_name_it == "availability_cantons"
    assert distribution_availability.wms_layer_name_en == "availability_cantons"
    assert distribution_availability.wms_layer_name_rm is None
    assert distribution_availability.meta_information is True
    assert distribution_availability.dataservice == dataservice_availability
    assert distribution_availability.dataset == dataset

    distribution_stac = ExternalStacDistribution.objects.get(
        distribution_id="ch.kgk.fixpunkte:stac"
    )
    assert distribution_stac.data_source == "geodienste"
    assert distribution_stac.title_de == "STAC Download Collection"
    assert distribution_stac.title_en == "STAC Download Collection"
    assert distribution_stac.title_fr == "STAC Download Collection"
    assert distribution_stac.title_it == "STAC Download Collection"
    assert distribution_stac.title_rm == "STAC Download Collection"
    assert distribution_stac.description_de is None
    assert distribution_stac.description_en is None
    assert distribution_stac.description_fr is None
    assert distribution_stac.description_it is None
    assert distribution_stac.description_rm is None
    assert distribution_stac.stac_collection_id == "fixpunkte"
    assert distribution_stac.meta_information is False
    assert distribution_stac.dataservice.dataservice_id == "stac-geodienste"
    assert distribution_stac.dataset == dataset

    dataset.refresh_from_db()
    assert dataset.preferred_distribution == distribution_data

    # ------
    # Update
    # ------
    dataservice_data.default_language = ""
    dataservice_data.languages = []
    dataservice_data.capabilities_url = "fixme"
    dataservice_data.save()

    distribution_data.wms_layer_name_de = "fixme"
    distribution_data.wms_layer_name_rm = "fixme"
    distribution_data.save()

    out = StringIO()
    call_command("import_geodienste", distributions=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataservice with dataservice_id wms-geodienste-fixpunkte already exists" in out
    assert "Dataservice with dataservice_id wms-geodienste-fixpunkte changed" in out
    assert (
        "Dataservice with dataservice_id wms-geodienste-fixpunkte-availability already exists"
        in out
    )
    assert "Distribution with distribution_id ch.kgk.fixpunkte:wms already exists" in out
    assert "Distribution with distribution_id ch.kgk.fixpunkte:wms changed" in out
    assert (
        "Distribution with distribution_id ch.kgk.fixpunkte-availability:wms already exists" in out
    )

    dataservice_data.refresh_from_db()
    assert dataservice_data.default_language == "de"
    assert dataservice_data.languages == ["de", "fr", "it", "en"]
    assert (
        dataservice_data.capabilities_url
        == "https://geodienste.ch/db/fixpunkte_0/{lang3}?SERVICE=WMS&REQUEST=GetCapabilities"
    )

    distribution_data.refresh_from_db()
    assert distribution_data.wms_layer_name_de == "daten"
    assert distribution_data.wms_layer_name_rm is None

    out = StringIO()
    call_command("import_geodienste", distributions=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataservice with dataservice_id wms-geodienste-fixpunkte already exists" in out
    assert "Dataservice with dataservice_id wms-geodienste-fixpunkte changed" not in out
    assert (
        "Dataservice with dataservice_id wms-geodienste-fixpunkte-availability already exists"
        in out
    )
    assert "Distribution with distribution_id ch.kgk.fixpunkte:wms already exists" in out
    assert "Distribution with distribution_id ch.kgk.fixpunkte:wms changed" not in out
    assert (
        "Distribution with distribution_id ch.kgk.fixpunkte-availability:wms already exists" in out
    )


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_additional_distributions(mock, client, db):
    dataset = Dataset(
        dataset_id="ch.kgk.av",
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="Abstract FR",
        title_short_de="Title DE",
        title_short_en="Title EN",
        title_short_fr="Title FR",
    )
    dataset.save()

    # ------
    # Create
    # ------
    mock.side_effect = api_response(
        services={
            "services": [
                {
                    "base_topic": "av",
                    "canton": "lu",
                    "broker": None,
                }
            ]
        },
        config={
            "de": {
                "av": {
                    "default": {
                        "layers": [{"name": "daten", "opacity": 0.9}],
                        "legend_layer": "daten",
                        "wms": "https://geodienste.ch/db/av_0/deu",
                        "swissgeo_distributions": [{"name": "fixpunkte", "opacity": 0.9}],
                    },
                    "languages": ["deu", "fra", "ita"],
                    "derivates": {},
                }
            },
            "fr": {
                "av": {
                    "default": {
                        "layers": [{"name": "donnees", "opacity": 0.9}],
                        "legend_layer": "donnees",
                        "wms": "https://geodienste.ch/db/av_0/fra",
                        "swissgeo_distributions": [{"name": "points_fixes", "opacity": 0.9}],
                    },
                    "languages": ["deu", "fra", "ita"],
                    "derivates": {},
                }
            },
            "it": {
                "av": {
                    "default": {
                        "layers": [{"name": "dati", "opacity": 0.9}],
                        "legend_layer": "dati",
                        "wms": "https://geodienste.ch/db/av_0/ita",
                        "swissgeo_distributions": [{"name": "punti_fissi", "opacity": 0.9}],
                    },
                    "languages": ["deu", "fra", "ita"],
                    "derivates": {},
                }
            },
            "en": {
                "av": {
                    "default": {
                        "layers": [{"name": "data", "opacity": 0.9}],
                        "legend_layer": "data",
                        "wms": "https://geodienste.ch/db/av_0/eng",
                        "swissgeo_distributions": [{"name": "fixpunkte", "opacity": 0.9}],
                    },
                    "languages": ["deu", "fra", "ita"],
                    "derivates": {},
                }
            },
        },
        capabilities={
            "de": b"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
                <WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms">
                    <Capability>
                        <Layer>
                            <Name>fixpunkte</Name>
                            <Title>Title DE</Title>
                            <Abstract>Abstract DE</Abstract>
                        </Layer>
                    </Capability>
                </WMS_Capabilities>""",
            "fr": b"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
                <WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms">
                    <Capability>
                        <Layer>
                            <Name>points_fixes</Name>
                            <Title>Title FR</Title>
                            <Abstract>Abstract FR</Abstract>
                        </Layer>
                    </Capability>
                </WMS_Capabilities>""",
            "it": b"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
                <WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms">
                    <Capability>
                        <Layer>
                            <Name>punti_fissi</Name>
                            <Title>Title IT</Title>
                            <Abstract>Abstract IT</Abstract>
                        </Layer>
                    </Capability>
                </WMS_Capabilities>""",
        },
    )

    out = StringIO()
    call_command("import_geodienste", distributions=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Distribution with distribution_id ch.kgk.av-fixpunkte:wms does not exist yet" in out

    dataservice = Dataservice.objects.get(dataservice_id="wms-geodienste-av")

    distribution = ExternalWMSDistribution.objects.get(distribution_id="ch.kgk.av-fixpunkte:wms")
    assert distribution.data_source == "geodienste"
    assert distribution.distribution_id == "ch.kgk.av-fixpunkte:wms"
    assert distribution.title_de == "Title DE"
    assert distribution.title_fr == "Title FR"
    assert distribution.title_it == "Title IT"
    assert distribution.title_en is None
    assert distribution.title_rm is None
    assert distribution.description_de == "Abstract DE"
    assert distribution.description_fr == "Abstract FR"
    assert distribution.description_it == "Abstract IT"
    assert distribution.description_en is None
    assert distribution.description_rm is None
    assert distribution.wms_layer_name_de == "fixpunkte"
    assert distribution.wms_layer_name_fr == "points_fixes"
    assert distribution.wms_layer_name_it == "punti_fissi"
    assert distribution.wms_layer_name_en is None
    assert distribution.wms_layer_name_rm is None
    assert distribution.opacity == Decimal("0.90")
    assert distribution.meta_information is False
    assert distribution.dataservice == dataservice
    assert distribution.dataset == dataset


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_additional_av_distributions(mock, client, db):  # noqa: PLR0915
    dataset = Dataset(
        dataset_id="ch.kgk.av",
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="Abstract FR",
        title_short_de="Title DE",
        title_short_en="Title EN",
        title_short_fr="Title FR",
    )
    dataset.save()

    # ------
    # Create
    # ------
    mock.side_effect = api_response(
        services={
            "services": [
                {
                    "base_topic": "av",
                    "canton": "lu",
                    "broker": None,
                }
            ]
        },
        config={
            "de": {
                "av": {
                    "default": {
                        "layers": [{"name": "daten", "opacity": 0.9}],
                        "legend_layer": "daten",
                        "wms": "https://geodienste.ch/db/av_0/deu",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita"],
                    "derivates": {
                        "24.0.0 (AV: Situationsplan (ÖREB))": {
                            "layers": [{"name": "daten", "opacity": 0.9}],
                            "legend_layer": "daten",
                            "wms": "https://dev2.geodienste.ch/db/av_situationsplan_oereb_0/deu",
                            "swissgeo_distributions": [],
                        },
                        "24.0.0 (AV: Situationsplan)": {
                            "layers": [{"name": "daten", "opacity": 0.9}],
                            "legend_layer": "daten",
                            "wms": "https://dev2.geodienste.ch/db/av_situationsplan_0/deu",
                            "swissgeo_distributions": [],
                        },
                        "24.0.0 (AV: Standard (farbig))": {
                            "layers": [{"name": "daten", "opacity": 0.9}],
                            "legend_layer": "daten",
                            "wms": "https://dev2.geodienste.ch/db/avc_0/deu",
                            "swissgeo_distributions": [],
                        },
                        "24.0.0 (AV: Standard (schwarz/weiss))": {
                            "layers": [{"name": "daten", "opacity": 0.9}],
                            "legend_layer": "daten",
                            "wms": "https://dev2.geodienste.ch/db/av_0/deu",
                            "swissgeo_distributions": [],
                        },
                    },
                }
            },
            "fr": {
                "av": {
                    "default": {
                        "layers": [{"name": "donnees", "opacity": 0.9}],
                        "legend_layer": "donnees",
                        "wms": "https://geodienste.ch/db/av_0/fra",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita"],
                    "derivates": {
                        "24.0.0 (MO : Plan de situation (RDPPF))": {
                            "layers": [{"name": "donnees", "opacity": 0.9}],
                            "legend_layer": "donnees",
                            "wms": "https://dev2.geodienste.ch/db/av_situationsplan_oereb_0/deu",
                            "swissgeo_distributions": [],
                        },
                        "24.0.0 (MO : Plan de situation)": {
                            "layers": [{"name": "donnees", "opacity": 0.9}],
                            "legend_layer": "donnees",
                            "wms": "https://dev2.geodienste.ch/db/av_situationsplan_0/deu",
                            "swissgeo_distributions": [],
                        },
                        "24.0.0 (MO: Standard (en couleur))": {
                            "layers": [{"name": "donnees", "opacity": 0.9}],
                            "legend_layer": "donnees",
                            "wms": "https://dev2.geodienste.ch/db/avc_0/deu",
                            "swissgeo_distributions": [],
                        },
                        "24.0.0 (MO : Standard (noir/blanc))": {
                            "layers": [{"name": "donnees", "opacity": 0.9}],
                            "legend_layer": "donnees",
                            "wms": "https://dev2.geodienste.ch/db/av_0/deu",
                            "swissgeo_distributions": [],
                        },
                    },
                }
            },
            "it": {
                "av": {
                    "default": {
                        "layers": [{"name": "dati", "opacity": 0.9}],
                        "legend_layer": "dati",
                        "wms": "https://geodienste.ch/db/av_0/ita",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita"],
                    "derivates": {
                        "24.0.0 (MU: piano di situazione (RDPP))": {
                            "layers": [{"name": "dati", "opacity": 0.9}],
                            "legend_layer": "dati",
                            "wms": "https://dev2.geodienste.ch/db/av_situationsplan_oereb_0/deu",
                            "swissgeo_distributions": [],
                        },
                        "24.0.0 (MU: piano di situazione)": {
                            "layers": [{"name": "dati", "opacity": 0.9}],
                            "legend_layer": "dati",
                            "wms": "https://dev2.geodienste.ch/db/av_situationsplan_0/deu",
                            "swissgeo_distributions": [],
                        },
                        "24.0.0 (MU: Standard (a colori))": {
                            "layers": [{"name": "dati", "opacity": 0.9}],
                            "legend_layer": "dati",
                            "wms": "https://dev2.geodienste.ch/db/avc_0/deu",
                            "swissgeo_distributions": [],
                        },
                        "24.0.0 (MU: Standard (nero/bianco))": {
                            "layers": [{"name": "dati", "opacity": 0.9}],
                            "legend_layer": "dati",
                            "wms": "https://dev2.geodienste.ch/db/av_0/deu",
                            "swissgeo_distributions": [],
                        },
                    },
                }
            },
            "en": {
                "av": {
                    "default": {
                        "layers": [{"name": "data", "opacity": 0.9}],
                        "legend_layer": "data",
                        "wms": "https://geodienste.ch/db/av_0/eng",
                    },
                    "languages": ["deu", "fra", "ita"],
                    "derivates": {
                        "24.0.0 (AV: Situationsplan (ÖREB))": {
                            "layers": [{"name": "data", "opacity": 1.0}],
                            "legend_layer": "data",
                            "wms": "https://dev2.geodienste.ch/db/av_situationsplan_oereb_0/deu",
                        },
                        "24.0.0 (AV: Situationsplan)": {
                            "layers": [{"name": "data", "opacity": 1.0}],
                            "legend_layer": "data",
                            "wms": "https://dev2.geodienste.ch/db/av_situationsplan_0/deu",
                        },
                        "24.0.0 (AV: Standard (farbig))": {
                            "layers": [{"name": "data", "opacity": 1.0}],
                            "legend_layer": "data",
                            "wms": "https://dev2.geodienste.ch/db/avc_0/deu",
                        },
                        "24.0.0 (AV: Standard (schwarz/weiss))": {
                            "layers": [{"name": "data", "opacity": 1.0}],
                            "legend_layer": "data",
                            "wms": "https://dev2.geodienste.ch/db/av_0/deu",
                        },
                    },
                }
            },
        },
    )

    out = StringIO()
    call_command("import_geodienste", distributions=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataservice with dataservice_id wms-geodienste-av does not exist yet" in out
    assert "Dataservice with dataservice_id wms-geodienste-av_situationsplan_oereb does not" in out
    assert "Dataservice with dataservice_id wms-geodienste-av_situationsplan does not exist" in out
    assert "Dataservice with dataservice_id wms-geodienste-avc does not exist yet" in out
    assert "Distribution with distribution_id ch.kgk.av:wms does not exist yet" in out
    assert "Distribution with distribution_id ch.kgk.av_situationsplan_oereb:wms does not" in out
    assert "Distribution with distribution_id ch.kgk.av_situationsplan:wms does not exist" in out
    assert "Distribution with distribution_id ch.kgk.avc:wms does not exist yet" in out
    assert "Setting ch.kgk.av:wms as preferred distribution for dataset ch.kgk.av" in out

    assert Dataservice.objects.count() == 5

    dataservice_1 = Dataservice.objects.get(dataservice_id="wms-geodienste-av")
    assert dataservice_1.data_source == "geodienste"
    assert dataservice_1.dataservice_id == "wms-geodienste-av"
    assert dataservice_1.default_language == "de"
    assert dataservice_1.languages == ["de", "fr", "it"]
    assert dataservice_1.title == "WMS geodienste.ch av"
    assert (
        dataservice_1.capabilities_url
        == "https://geodienste.ch/db/av_0/{lang3}?SERVICE=WMS&REQUEST=GetCapabilities"
    )

    dataservice_2 = Dataservice.objects.get(dataservice_id="wms-geodienste-av_situationsplan_oereb")
    assert dataservice_2.data_source == "geodienste"
    assert dataservice_2.dataservice_id == "wms-geodienste-av_situationsplan_oereb"
    assert dataservice_2.default_language == "de"
    assert dataservice_2.languages == ["de", "fr", "it"]
    assert dataservice_2.title == "WMS geodienste.ch av_situationsplan_oereb"
    assert (
        dataservice_2.capabilities_url
        == "https://dev2.geodienste.ch/db/av_situationsplan_oereb_0/{lang3}?SERVICE=WMS&REQUEST=GetCapabilities"
    )

    dataservice_3 = Dataservice.objects.get(dataservice_id="wms-geodienste-av_situationsplan")
    assert dataservice_3.data_source == "geodienste"
    assert dataservice_3.dataservice_id == "wms-geodienste-av_situationsplan"
    assert dataservice_3.default_language == "de"
    assert dataservice_3.languages == ["de", "fr", "it"]
    assert dataservice_3.title == "WMS geodienste.ch av_situationsplan"
    assert (
        dataservice_3.capabilities_url
        == "https://dev2.geodienste.ch/db/av_situationsplan_0/{lang3}?SERVICE=WMS&REQUEST=GetCapabilities"
    )

    dataservice_4 = Dataservice.objects.get(dataservice_id="wms-geodienste-avc")
    assert dataservice_4.data_source == "geodienste"
    assert dataservice_4.dataservice_id == "wms-geodienste-avc"
    assert dataservice_4.default_language == "de"
    assert dataservice_4.languages == ["de", "fr", "it"]
    assert dataservice_4.title == "WMS geodienste.ch avc"
    assert (
        dataservice_4.capabilities_url
        == "https://dev2.geodienste.ch/db/avc_0/{lang3}?SERVICE=WMS&REQUEST=GetCapabilities"
    )

    distribution_1 = ExternalWMSDistribution.objects.get(distribution_id="ch.kgk.av:wms")
    assert distribution_1.data_source == "geodienste"
    assert distribution_1.distribution_id == "ch.kgk.av:wms"
    assert distribution_1.title_de == "Title DE"
    assert distribution_1.title_fr == "Title FR"
    assert distribution_1.title_en == "Title EN"
    assert distribution_1.title_it is None
    assert distribution_1.title_rm is None
    assert distribution_1.description_de == "Abstract DE"
    assert distribution_1.description_fr == "Abstract FR"
    assert distribution_1.description_en == "Abstract EN"
    assert distribution_1.description_it is None
    assert distribution_1.description_rm is None
    assert distribution_1.wms_layer_name_de == "daten"
    assert distribution_1.wms_layer_name_fr == "donnees"
    assert distribution_1.wms_layer_name_it == "dati"
    assert distribution_1.wms_layer_name_en is None
    assert distribution_1.wms_layer_name_rm is None
    assert distribution_1.opacity == Decimal("0.90")
    assert distribution_1.meta_information is False
    assert distribution_1.dataservice == dataservice_1
    assert distribution_1.dataset == dataset

    distribution_2 = ExternalWMSDistribution.objects.get(
        distribution_id="ch.kgk.av_situationsplan_oereb:wms"
    )
    assert distribution_2.data_source == "geodienste"
    assert distribution_2.distribution_id == "ch.kgk.av_situationsplan_oereb:wms"
    assert distribution_2.title_de == "Situationsplan (ÖREB)"
    assert distribution_2.title_en is None
    assert distribution_2.title_fr == "Plan de situation (RDPPF)"
    assert distribution_2.title_it == "piano di situazione (RDPP)"
    assert distribution_2.title_rm is None
    assert distribution_2.description_de == "Abstract DE"
    assert distribution_2.description_en == "Abstract EN"
    assert distribution_2.description_fr == "Abstract FR"
    assert distribution_2.description_it is None
    assert distribution_2.description_rm is None
    assert distribution_2.wms_layer_name_de == "daten"
    assert distribution_2.wms_layer_name_fr == "donnees"
    assert distribution_2.wms_layer_name_it == "dati"
    assert distribution_2.wms_layer_name_en is None
    assert distribution_2.wms_layer_name_rm is None
    assert distribution_2.opacity == Decimal("0.90")
    assert distribution_2.meta_information is False
    assert distribution_2.dataservice == dataservice_2
    assert distribution_2.dataset == dataset

    distribution_2 = ExternalWMSDistribution.objects.get(
        distribution_id="ch.kgk.av_situationsplan:wms"
    )
    assert distribution_2.data_source == "geodienste"
    assert distribution_2.distribution_id == "ch.kgk.av_situationsplan:wms"
    assert distribution_2.title_de == "Situationsplan"
    assert distribution_2.title_en is None
    assert distribution_2.title_fr == "Plan de situation"
    assert distribution_2.title_it == "piano di situazione"
    assert distribution_2.title_rm is None
    assert distribution_2.description_de == "Abstract DE"
    assert distribution_2.description_en == "Abstract EN"
    assert distribution_2.description_fr == "Abstract FR"
    assert distribution_2.description_it is None
    assert distribution_2.description_rm is None
    assert distribution_2.wms_layer_name_de == "daten"
    assert distribution_2.wms_layer_name_fr == "donnees"
    assert distribution_2.wms_layer_name_it == "dati"
    assert distribution_2.wms_layer_name_en is None
    assert distribution_2.wms_layer_name_rm is None
    assert distribution_2.opacity == Decimal("0.90")
    assert distribution_2.meta_information is False
    assert distribution_2.dataservice == dataservice_3
    assert distribution_2.dataset == dataset

    distribution_3 = ExternalWMSDistribution.objects.get(distribution_id="ch.kgk.avc:wms")
    assert distribution_3.data_source == "geodienste"
    assert distribution_3.distribution_id == "ch.kgk.avc:wms"
    assert distribution_3.title_de == "Standard (farbig)"
    assert distribution_3.title_en is None
    assert distribution_3.title_fr == "Standard (en couleur)"
    assert distribution_3.title_it == "Standard (a colori)"
    assert distribution_3.title_rm is None
    assert distribution_3.description_de == "Abstract DE"
    assert distribution_3.description_en == "Abstract EN"
    assert distribution_3.description_fr == "Abstract FR"
    assert distribution_3.description_it is None
    assert distribution_3.description_rm is None
    assert distribution_3.wms_layer_name_de == "daten"
    assert distribution_3.wms_layer_name_fr == "donnees"
    assert distribution_3.wms_layer_name_it == "dati"
    assert distribution_3.wms_layer_name_en is None
    assert distribution_3.wms_layer_name_rm is None
    assert distribution_3.opacity == Decimal("0.90")
    assert distribution_3.meta_information is False
    assert distribution_3.dataservice == dataservice_4
    assert distribution_3.dataset == dataset

    dataset.refresh_from_db()
    assert dataset.preferred_distribution == distribution_1


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_cleans_distributions(mock, client, db):
    dataset = Dataset(
        dataset_id="ch.kgk.av",
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="Abstract FR",
        title_short_de="Title DE",
        title_short_en="Title EN",
        title_short_fr="Title FR",
    )
    dataset.save()

    WMSDataservice(
        dataservice_id="obsolete",
        data_source=Dataservice.DataSource.GEODIENSTE,
        data_source_ids=[],
    ).save()
    WMSDataservice(
        dataservice_id="removed",
        data_source=Dataservice.DataSource.GEODIENSTE,
        data_source_ids=["removed"],
    ).save()

    ExternalWMSDistribution(
        distribution_id="obsolete",
        data_source=Distribution.DataSource.GEODIENSTE,
        data_source_ids=[],
        wms_layer_name_de="daten",
        dataset=dataset,
    ).save()
    ExternalWMSDistribution(
        distribution_id="removed",
        data_source=Distribution.DataSource.GEODIENSTE,
        data_source_ids=["removed"],
        wms_layer_name_de="daten",
        dataset=dataset,
    ).save()

    mock.side_effect = api_response(
        services={
            "services": [
                {
                    "base_topic": "av",
                    "canton": "lu",
                    "broker": None,
                    "getcapabilities_wms": [
                        "https://geodienste.ch/db/av_0/deu?SERVICE=WMS&REQUEST=GetCapabilities"
                    ],
                }
            ]
        },
        config={
            "de": {
                "av": {
                    "default": {
                        "layers": [{"name": "daten", "opacity": 0.9}],
                        "legend_layer": "daten",
                        "wms": "https://geodienste.ch/db/av_0/deu",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita", "eng"],
                    "derivates": {},
                }
            },
            "fr": {
                "av": {
                    "default": {
                        "layers": [{"name": "donnees", "opacity": 0.9}],
                        "legend_layer": "donnees",
                        "wms": "https://geodienste.ch/db/av_0/fra",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita", "eng"],
                    "derivates": {},
                }
            },
            "it": {
                "av": {
                    "default": {
                        "layers": [{"name": "dati", "opacity": 0.9}],
                        "legend_layer": "dati",
                        "wms": "https://geodienste.ch/db/av_0/ita",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita", "eng"],
                    "derivates": {},
                }
            },
            "en": {
                "av": {
                    "default": {
                        "layers": [{"name": "data", "opacity": 0.9}],
                        "legend_layer": "data",
                        "wms": "https://geodienste.ch/db/av_0/eng",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita", "eng"],
                    "derivates": {},
                }
            },
        },
    )

    # --------
    # No clean
    # --------
    out = StringIO()
    call_command("import_geodienste", distributions=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removed data_source_ids (dataservice) found: removed" in out
    assert "Obsolete dataservices found: obsolete" in out
    assert "Removed data_source_ids (distribution) found: removed" in out
    assert "Obsolete distributions found: obsolete" in out

    assert Dataservice.objects.count() == 4
    assert Distribution.objects.count() == 4

    # --------
    # Clean
    # --------
    out = StringIO()
    call_command("import_geodienste", distributions=True, clean=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removing obsolete data_source_id (dataservice) removed" in out
    assert "Removing obsolete dataservice obsolete" in out
    assert "Removing obsolete dataservice removed" in out
    assert "Removing obsolete data_source_id (distribution) removed" in out
    assert "Removing obsolete distribution obsolete" in out
    assert "Removing obsolete distribution removed" in out

    assert Dataservice.objects.count() == 2
    assert Distribution.objects.count() == 2


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_useses_dataset_mapping_for_distributions(mock, client, db):
    Dataset(
        dataset_id="ch.kgk.av",
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="Abstract FR",
        title_short_de="Title DE",
        title_short_en="Title EN",
        title_short_fr="Title FR",
    ).save()
    dataset = Dataset(
        dataset_id="ch.kgk-cgc.av",
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="Abstract FR",
        title_short_de="Title DE",
        title_short_en="Title EN",
        title_short_fr="Title FR",
    )
    dataset.save()

    DatasetMapping(dataset_id_prefix="ch.kgk.av", dataset_id="ch.kgk-cgc.av").save()

    mock.side_effect = api_response(
        services={
            "services": [
                {
                    "base_topic": "av",
                    "canton": "lu",
                    "broker": None,
                    "getcapabilities_wms": [
                        "https://geodienste.ch/db/av_0/deu?SERVICE=WMS&REQUEST=GetCapabilities"
                    ],
                }
            ]
        },
        config={
            "de": {
                "av": {
                    "default": {
                        "layers": [{"name": "daten", "opacity": 0.9}],
                        "legend_layer": "daten",
                        "wms": "https://geodienste.ch/db/av_0/deu",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita", "eng"],
                    "derivates": {},
                }
            },
            "fr": {
                "av": {
                    "default": {
                        "layers": [{"name": "donnees", "opacity": 0.9}],
                        "legend_layer": "donnees",
                        "wms": "https://geodienste.ch/db/av_0/fra",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita", "eng"],
                    "derivates": {},
                }
            },
            "it": {
                "av": {
                    "default": {
                        "layers": [{"name": "dati", "opacity": 0.9}],
                        "legend_layer": "dati",
                        "wms": "https://geodienste.ch/db/av_0/ita",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita", "eng"],
                    "derivates": {},
                }
            },
            "en": {
                "av": {
                    "default": {
                        "layers": [{"name": "data", "opacity": 0.9}],
                        "legend_layer": "data",
                        "wms": "https://geodienste.ch/db/av_0/eng",
                        "swissgeo_distributions": [],
                    },
                    "languages": ["deu", "fra", "ita", "eng"],
                    "derivates": {},
                }
            },
        },
    )

    out = StringIO()
    call_command("import_geodienste", distributions=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataset mapping found for dataset_id ch.kgk.av: ch.kgk-cgc.av" in out
    assert "Setting ch.kgk.av:wms as preferred distribution for dataset ch.kgk-cgc.av" in out

    dataset.refresh_from_db()
    assert dataset.preferred_distribution.distribution_id == "ch.kgk.av:wms"
