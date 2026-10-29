from unittest.mock import patch

from dataset.models import Dataset, DatasetToUnit
from harvest.models import (
    DatasetMapping,
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
        "abbreviation_de": "abbreviation_de",
        "abbreviation_fr": "abbreviation_fr",
        "abbreviation_en": "abbreviation_en",
    }
    Organization(organization_id="ch.a", **attributes).save()
    Organization(organization_id="ch.b", **attributes).save()

    OrganizationMapping(provider_id_prefix="ch.a.b", organization_id="ch.b").save()
    OrganizationMapping(provider_id_prefix="ch.a.c", organization_id="ch.c").save()
    OrganizationMapping(provider_id_prefix="ch.d", organization_id="ch.a").save()
    OrganizationMapping(provider_id_prefix="ch.e", organization_id="ch.c").save()

    assert OrganizationMapping.objects.get_by_natural_key(
        provider_id_prefix="ch.a.b", organization_id="ch.b"
    )
    assert OrganizationMapping.objects.get_by_natural_key(
        provider_id_prefix="ch.a.c", organization_id="ch.c"
    )
    assert OrganizationMapping.objects.get_by_natural_key(
        provider_id_prefix="ch.d", organization_id="ch.a"
    )
    assert OrganizationMapping.objects.get_by_natural_key(
        provider_id_prefix="ch.e", organization_id="ch.c"
    )

    table = OrganizationMapping.table()

    assert table.match("ch.a.b")[0].organization_id == "ch.b"
    assert table.match("ch.a.c")[0] is None
    assert table.match("ch.d.e")[0].organization_id == "ch.a"
    assert table.match("ch.e.f")[0] is None


def test_dataset_mapping(db):
    attributes = {
        "title_de": "title__de",
        "title_fr": "title_fr",
        "title_en": "title_en",
        "description_de": "description_de",
        "description_fr": "description_fr",
        "description_en": "description_en",
    }
    Dataset(dataset_id="ch.a", geocat_id="ch.a", **attributes).save()
    Dataset(dataset_id="ch.b", geocat_id="ch.b", **attributes).save()

    DatasetMapping(dataset_id_prefix="ch.a.b", dataset_id="ch.b").save()
    DatasetMapping(dataset_id_prefix="ch.a.c", dataset_id="ch.c").save()
    DatasetMapping(dataset_id_prefix="ch.d", dataset_id="ch.a").save()
    DatasetMapping(dataset_id_prefix="ch.e", dataset_id="ch.c").save()

    assert DatasetMapping.objects.get_by_natural_key(dataset_id_prefix="ch.a.b", dataset_id="ch.b")
    assert DatasetMapping.objects.get_by_natural_key(dataset_id_prefix="ch.a.c", dataset_id="ch.c")
    assert DatasetMapping.objects.get_by_natural_key(dataset_id_prefix="ch.d", dataset_id="ch.a")
    assert DatasetMapping.objects.get_by_natural_key(dataset_id_prefix="ch.e", dataset_id="ch.c")

    table = DatasetMapping.table()

    assert table.match("ch.a.b")[0].dataset_id == "ch.b"
    assert table.match("ch.a.c")[0] is None
    assert table.match("ch.d.e")[0].dataset_id == "ch.a"
    assert table.match("ch.e.f")[0] is None


@patch("organization.models.Client")
def test_dataset_to_unit_mapping(client, db):
    names = {"name_de": "name_de", "name_fr": "name_fr", "name_en": "name_en"}
    abbreviations = {
        "abbreviation_de": "abbreviation_de",
        "abbreviation_fr": "abbreviation_fr",
        "abbreviation_en": "abbreviation_en",
    }

    org_a = Organization(organization_id="ch.a", **names, **abbreviations)
    org_a.save()
    org_b = Organization(organization_id="ch.b", **names, **abbreviations)
    org_b.save()

    Unit(unit_id="x", organization=org_a, **names).save()
    Unit(unit_id="x", organization=org_b, **names).save()
    Unit(unit_id="y", organization=org_b, **names).save()

    role = DatasetToUnit.Role.OWNER

    DatasetToUnitMapping(dataset_id_prefix="d.1", organization_id="ch.a", role=role).save()
    DatasetToUnitMapping(
        dataset_id_prefix="d.1.1",
        organization_id="ch.a",
        unit_id="x",
        role=role,
    ).save()
    DatasetToUnitMapping(
        dataset_id_prefix="d.2", organization_id="ch.a", unit_id="z", role=role
    ).save()
    DatasetToUnitMapping(
        dataset_id_prefix="d.2.1",
        organization_id="ch.b",
        unit_id="y",
        role=role,
    ).save()

    assert DatasetToUnitMapping.objects.get_by_natural_key(
        dataset_id_prefix="d.1", organization_id="ch.a", unit_id="default", role=role
    )
    assert DatasetToUnitMapping.objects.get_by_natural_key(
        dataset_id_prefix="d.1.1",
        organization_id="ch.a",
        unit_id="x",
        role=role,
    )
    assert DatasetToUnitMapping.objects.get_by_natural_key(
        dataset_id_prefix="d.2", organization_id="ch.a", unit_id="z", role=role
    )
    assert DatasetToUnitMapping.objects.get_by_natural_key(
        dataset_id_prefix="d.2.1",
        organization_id="ch.b",
        unit_id="y",
        role=role,
    )

    table = DatasetToUnitMapping.table()

    assert table[role].match("d.1")[0].unit_id == "default"
    assert table[role].match("d.1")[0].organization.organization_id == "ch.a"

    assert table[role].match("d.1.1")[0].unit_id == "x"
    assert table[role].match("d.1.1")[0].organization.organization_id == "ch.a"

    assert table[role].match("d.1.2")[0].unit_id == "default"
    assert table[role].match("d.1.2")[0].organization.organization_id == "ch.a"

    assert table[role].match("d.2") == (None, None)

    assert table[role].match("d.2.1")[0].unit_id == "y"
    assert table[role].match("d.2.1")[0].organization.organization_id == "ch.b"

    assert table[role].match("d.3") == (None, None)


@patch("organization.models.Client")
def test_dataset_to_contact_mapping(client, db):
    attributes = {
        "name_de": "name_de",
        "name_fr": "name_fr",
        "name_en": "name_en",
        "abbreviation_de": "abbreviation_de",
        "abbreviation_fr": "abbreviation_fr",
        "abbreviation_en": "abbreviation_en",
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

    assert DatasetToContactMapping.objects.get_by_natural_key(
        dataset_id_prefix="d.1", role="owner", organization_id="ch.a", contact_name_en="x"
    )
    assert DatasetToContactMapping.objects.get_by_natural_key(
        dataset_id_prefix="d.1.1",
        role="pointOfContact",
        organization_id="ch.b",
        contact_name_en="y",
    )
    assert DatasetToContactMapping.objects.get_by_natural_key(
        dataset_id_prefix="d.2", role="pointOfContact", organization_id="ch.b", contact_name_en="z"
    )

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
