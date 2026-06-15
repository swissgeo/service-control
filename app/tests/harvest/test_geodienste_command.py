from io import StringIO
from json import dumps
from unittest.mock import patch

from django.core.management import call_command

from harvest.models import OrganizationMapping
from organization.models import Contact, Organization


# --------------------------------------------------------------------------------------------------
# Organizations
# --------------------------------------------------------------------------------------------------
@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_aggregate_organization(mock, client, db):
    mock.return_value.json.return_value = {
        "services": [{"base_topic": "av", "canton": "LU", "broker": None}]
    }

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

    mock.return_value.json.return_value = {
        "services": [{"base_topic": "av", "canton": "LU", "broker": None}]
    }

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

    mock.return_value.json.return_value = {
        "services": [{"base_topic": "av", "canton": "LU", "broker": None}]
    }

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
    mock.return_value.json.return_value = {
        "services": [{"base_topic": "av", "canton": "LU", "broker": None}]
    }

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

    mock.return_value.json.return_value = {
        "services": [{"base_topic": "av", "canton": "LU", "broker": None}]
    }

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
    mock.return_value.json.return_value = {"services": [{"broker": "BFE"}]}

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

    mock.return_value.json.return_value = {
        "services": [{"base_topic": "av", "canton": None, "broker": "BFE"}]
    }

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
    file = tmp_path / "services.json"
    file.write_text(dumps({"services": [{"broker": "BFE"}]}))

    out = StringIO()
    call_command(
        "import_geodienste", organizations=True, services_endpoint=file, verbosity=2, stdout=out
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

    mock.return_value.json.return_value = {
        "services": [{"base_topic": "av", "canton": "LU", "broker": None}]
    }

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

    mock.return_value.json.return_value = {
        "services": [{"canton": "LU", "broker": None, "base_topic": "av"}]
    }

    # --------
    # No clean
    # --------
    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removed data_source_ids (provider) found: removed" in out
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
    mock.return_value.json.return_value = {
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

    out = StringIO()
    call_command("import_geodienste", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.kgk does not exist, skipping" in out


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_aggregate_contact(mock, client, db):
    mock.return_value.json.return_value = {
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
    mock.return_value.json.return_value = {
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
    mock.return_value.json.return_value = {
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
    mock.return_value.json.return_value = {
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

    assert "Removed data_source_ids (provider) found: removed" in out
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
    mock.return_value.json.return_value = {
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

    out = StringIO()
    call_command("import_geodienste", contacts=True, clean=False, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Contact LU for organization ch.geodienste-lu already exists" in out
    assert "Contact LU for organization ch.geodienste-lu updated" in out
    assert "Contact LU.av for organization ch.geodienste-lu already exists" in out
    assert "Contact LU.av for organization ch.geodienste-lu updated" in out
    assert "Removed data_source_ids (provider) found: LU.gefahrenkarten, removed" in out
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

    mock.return_value.json.return_value = {
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
