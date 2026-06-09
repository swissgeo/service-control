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
def test_command_creates_cantonal_organization(mock, client, db):
    mock.return_value.json.return_value = {
        "services": [{"base_topic": "av", "canton": "LU", "broker": None}]
    }

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.lu does not exist yet, creating a new one." in out

    org = Organization.objects.first()
    assert org
    assert org.organization_id == "ch.lu"
    assert org.name_de == "Kanton Luzern"
    assert org.name_en == "Canton of Lucerne"
    assert org.name_fr == "Canton de Lucerne"
    assert org.name_it == "Cantone di Lucerna"
    assert org.name_rm == "Chantun Lucerna"
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

    assert "Organization with organization_id ch.lu already exists" in out


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_broker_organization(mock, client, db):
    mock.return_value.json.return_value = {
        "services": [{"base_topic": "av", "canton": "Broker", "broker": "BFE"}]
    }

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with organization_id ch.bfe does not exist yet, creating a new one." in out

    org = Organization.objects.first()
    assert org
    assert org.organization_id == "ch.bfe"
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
def test_command_creates_organization_from_file(client, db, tmp_path):
    file = tmp_path / "services_de.json"
    file.write_text(
        dumps({"services": [{"base_topic": "av", "canton": "Broker", "broker": "BFE"}]})
    )

    out = StringIO()
    call_command(
        "import_geodienste", organizations=True, services_endpoint=tmp_path, verbosity=2, stdout=out
    )
    out = out.getvalue()

    assert "Organization with organization_id ch.bfe does not exist yet, creating a new one." in out


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_uses_organization_mapping(mock, client, db):
    org_1 = Organization(
        organization_id="ch.lu-new",
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
        organization_id="ch.lu",
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

    OrganizationMapping(provider_id_prefix="LU", organization_id="ch.lu-new", update=True).save()

    mock.return_value.json.return_value = {
        "services": [{"base_topic": "av", "canton": "LU", "broker": None}]
    }

    out = StringIO()
    call_command("import_geodienste", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id LU: ch.lu-new" in out

    org_1.refresh_from_db()
    assert org_1.organization_id == "ch.lu-new"
    assert org_1.data_source_ids == ["LU"]

    org_2.refresh_from_db()
    assert org_2.data_source_ids == []


# --------------------------------------------------------------------------------------------------
# Contacts
# --------------------------------------------------------------------------------------------------
@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_creates_updates_cleans_contact(mock, client, db):
    org = Organization(
        organization_id="ch.lu",
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
                "canton": "Broker",
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

    assert "Contact LU.contact_geo for organization ch.lu does not exist yet, creating" in out
    assert "Contact LU.av for organization ch.lu does not exist yet, creating" in out
    assert "Contact LU.gefahrenkarten for organization ch.lu does not exist yet, creating" in out
    assert "Contact LU.contact_geo for organization ch.lu already exists" in out
    assert "Organization with organization_id ch.missing does not exist, skipping" in out
    assert "Removed data_source_ids (provider) found: removed" in out
    assert "Obsolete contacts found: ch.lu (obsolete)" in out

    assert Contact.objects.count() == 6
    assert {
        (tuple(contact.data_source_ids), contact.legacy_contact)
        for contact in org.contact_set.all()
    } == {
        ((), "obsolete"),
        (("removed",), "removed"),
        ((), "geocat"),
        (("LU.contact_geo",), "Foo"),
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

    assert "Contact LU.contact_geo for organization ch.lu already exists" in out
    assert "Contact LU.contact_geo for organization ch.lu changed, updating" in out
    assert "Contact LU.av for organization ch.lu already exists" in out
    assert "Contact LU.av for organization ch.lu changed, updating" in out
    assert "Removed data_source_ids (provider) found: LU.gefahrenkarten, removed" in out
    assert "Obsolete contacts found: ch.lu (obsolete)" in out

    assert Contact.objects.count() == 6
    assert {
        (tuple(contact.data_source_ids), contact.legacy_contact)
        for contact in org.contact_set.all()
    } == {
        ((), "obsolete"),
        (("removed",), "removed"),
        ((), "geocat"),
        (("LU.contact_geo",), "Foobar"),
        (("LU.av",), "Quux"),
        (("LU.gefahrenkarten",), "Baz"),
    }

    # --------------
    # Clean
    # --------------

    out = StringIO()
    call_command("import_geodienste", contacts=True, clean=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Contact LU.contact_geo for organization ch.lu already exists" in out
    assert "Contact LU.av for organization ch.lu already exists" in out
    assert "Removing obsolete data_source_id (contact) removed" in out
    assert "Removing obsolete data_source_id (contact) LU.gefahrenkarten" in out
    assert "Removing obsolete contact ch.lu (obsolete)" in out
    assert "Removing obsolete contact ch.lu (removed)" in out
    assert "Removing obsolete contact ch.lu (None)" in out

    assert Contact.objects.count() == 3
    assert {
        (tuple(contact.data_source_ids), contact.legacy_contact)
        for contact in org.contact_set.all()
    } == {((), "geocat"), (("LU.contact_geo",), "Foobar"), (("LU.av",), "Quux")}


@patch("organization.models.Client")
@patch("harvest.management.commands.import_geodienste.get", name="get")
def test_command_organization_mapping_for_contact(mock, client, db):
    org = Organization(
        organization_id="ch.lu",
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
    org.save()

    OrganizationMapping(provider_id_prefix="LU", organization_id="ch.lu", update=True).save()

    mock.return_value.json.return_value = {
        "services": [
            {
                "canton": "LU",
                "broker": None,
                "base_topic": "av",
                "contact_geo": "Foo",
            }
        ]
    }

    out = StringIO()
    call_command("import_geodienste", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id LU: ch.lu" in out
    assert "Contact LU.contact_geo for organization ch.lu does not exist yet" in out

    assert Contact.objects.count() == 1
    assert {
        (tuple(contact.data_source_ids), contact.legacy_contact)
        for contact in org.contact_set.all()
    } == {(("LU.contact_geo",), "Foo")}
