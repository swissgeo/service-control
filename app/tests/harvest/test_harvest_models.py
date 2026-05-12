from unittest.mock import patch

from harvest.models import (
    DatasetToContactMapping,
    DatasetToUnitMapping,
    OrganizationMapping,
    PrefixLookupTable,
)
from organization.models import Contact, Organization, Unit


def test_prefix_lookup_table():
    table: PrefixLookupTable[str] = PrefixLookupTable(
        {"abc": ("abc", 1), "a": ("a", 2), "ab": ("ab", 3)}
    )

    assert table.table == {"a": ("a", 2), "ab": ("ab", 3), "abc": ("abc", 1)}

    assert table.match("-") == (None, None)
    assert table.match("a") == ("a", 2)
    assert table.match("ab") == ("ab", 3)
    assert table.match("abc") == ("abc", 1)
    assert table.match("abcd") == ("abc", 1)


@patch("organization.models.Client")
def test_organization_mapping(client, db):
    attributes = {
        "name_de": "name_de",
        "name_fr": "name_fr",
        "name_en": "name_en",
        "acronym_de": "acronym_de",
        "acronym_fr": "acronym_fr",
        "acronym_en": "acronym_en",
    }
    Organization(organization_id="ch.a", **attributes).save()
    Organization(organization_id="ch.b", **attributes).save()

    OrganizationMapping(provider_id_prefix="ch.a.b", organization_id="ch.b").save()
    OrganizationMapping(provider_id_prefix="ch.a.c", organization_id="ch.c").save()
    OrganizationMapping(provider_id_prefix="ch.d", organization_id="ch.a").save()
    OrganizationMapping(provider_id_prefix="ch.e", organization_id="ch.c").save()

    table = OrganizationMapping.table()

    assert table.match("ch.a.b")[0].organization_id == "ch.b"
    assert table.match("ch.a.c")[0] is None
    assert table.match("ch.d.e")[0].organization_id == "ch.a"
    assert table.match("ch.e.f")[0] is None


@patch("organization.models.Client")
def test_dataset_to_unit_mapping(client, db):
    names = {"name_de": "name_de", "name_fr": "name_fr", "name_en": "name_en"}
    acronyms = {"acronym_de": "acronym_de", "acronym_fr": "acronym_fr", "acronym_en": "acronym_en"}

    org_a = Organization(organization_id="ch.a", **names, **acronyms)
    org_a.save()
    org_b = Organization(organization_id="ch.b", **names, **acronyms)
    org_b.save()

    Unit(unit_id="x", organization=org_a, **names).save()
    Unit(unit_id="x", organization=org_b, **names).save()
    Unit(unit_id="y", organization=org_b, **names).save()

    DatasetToUnitMapping(dataset_id_prefix="d.1", organization_id="ch.a").save()
    DatasetToUnitMapping(dataset_id_prefix="d.1.1", organization_id="ch.a", unit_id="x").save()
    DatasetToUnitMapping(dataset_id_prefix="d.2", organization_id="ch.a", unit_id="z").save()
    DatasetToUnitMapping(dataset_id_prefix="d.2.1", organization_id="ch.b", unit_id="y").save()

    table = DatasetToUnitMapping.table()

    assert table.match("d.1")[0].unit_id == "default"
    assert table.match("d.1")[0].organization.organization_id == "ch.a"

    assert table.match("d.1.1")[0].unit_id == "x"
    assert table.match("d.1.1")[0].organization.organization_id == "ch.a"

    assert table.match("d.1.2")[0].unit_id == "default"
    assert table.match("d.1.2")[0].organization.organization_id == "ch.a"

    assert table.match("d.2") == (None, None)

    assert table.match("d.2.1")[0].unit_id == "y"
    assert table.match("d.2.1")[0].organization.organization_id == "ch.b"

    assert table.match("d.3") == (None, None)


@patch("organization.models.Client")
def test_dataset_to_contact_mapping(client, db):
    attributes = {
        "name_de": "name_de",
        "name_fr": "name_fr",
        "name_en": "name_en",
        "acronym_de": "acronym_de",
        "acronym_fr": "acronym_fr",
        "acronym_en": "acronym_en",
    }
    org_a = Organization(organization_id="ch.a", **attributes)
    org_a.save()
    org_b = Organization(organization_id="ch.b", **attributes)
    org_b.save()

    Contact(name_en="x", organization=org_a).save()
    Contact(name_en="x", organization=org_b).save()
    Contact(name_en="y", organization=org_b).save()

    DatasetToContactMapping(
        dataset_id_prefix="d.1", role="owner", organization_id="ch.a", contact_name_en="x"
    ).save()
    DatasetToContactMapping(
        dataset_id_prefix="d.1.1",
        role="pointOfContact",
        organization_id="ch.b",
        contact_name_en="y",
    ).save()
    DatasetToContactMapping(
        dataset_id_prefix="d.2", role="pointOfContact", organization_id="ch.b", contact_name_en="z"
    ).save()

    table = DatasetToContactMapping.table()

    assert set(table.keys()) == {"owner", "pointOfContact"}

    assert table["owner"].match("d.1")[0].name_en == "x"
    assert table["owner"].match("d.1")[0].organization.organization_id == "ch.a"
    assert table["pointOfContact"].match("d.1") == (None, None)

    assert table["owner"].match("d.1.1")[0].name_en == "x"
    assert table["owner"].match("d.1.1")[0].organization.organization_id == "ch.a"
    assert table["pointOfContact"].match("d.1.1")[0].name_en == "y"
    assert table["pointOfContact"].match("d.1.1")[0].organization.organization_id == "ch.b"

    assert table["owner"].match("d.1.2")[0].name_en == "x"
    assert table["owner"].match("d.1.2")[0].organization.organization_id == "ch.a"
    assert table["pointOfContact"].match("d.1.2") == (None, None)

    assert table["owner"].match("d.2") == (None, None)
    assert table["pointOfContact"].match("d.2") == (None, None)

    assert table["owner"].match("d.3") == (None, None)
    assert table["pointOfContact"].match("d.3") == (None, None)
