from pydantic import ValidationError

import pytest

from dataset.models import Dataset, DatasetToContact
from distribution.models import ExternalGeoJSONDistribution
from export.export_models import (
    Contact,
    OARDataset,
    OARDistribution,
    RelativeLink,
    UnvalidatedLink,
)


def _legacy_contact(**overrides) -> dict:
    """A legacy contact as stored in `Dataset.legacy_contacts` by the harvest import."""
    contact = {
        "role": "pointOfContact",
        "org_name": "Bundesamt für Landestopografie swisstopo",
        "org_name_de": "Bundesamt für Landestopografie swisstopo",
        "org_name_fr": "Office fédéral de topographie swisstopo",
        "org_name_en": "Federal Office of Topography swisstopo",
        "org_name_it": "Ufficio federale di topografia swisstopo",
        "org_name_rm": "Uffizi federal da topografia swisstopo",
        "position_name_de": "Geodatenabgabe",
        "position_name_fr": "Distribution des géodonnées",
        "position_name_en": None,
        "position_name_it": None,
        "position_name_rm": None,
        "contact_voice": "+41 58 469 01 11",
        "contact_facsimile": "+41 58 469 04 59",
        "contact_sms": "+41 79 123 45 67",
        "contact_city": "Wabern",
        "contact_administrative_area": None,
        "contact_postal_code": "3084",
        "contact_delivery_point": "Seftigenstrasse 264",
        "contact_country": "CH",
        "contact_electronic_mail_addresses": ["geodata@swisstopo.ch", "another@test.ch"],
        "online_resources": [
            {
                "url": "http://www.swisstopo.ch",
                "url_de": "http://www.swisstopo.ch",
                "url_fr": "http://www.swisstopo.ch/fr",
                "url_en": None,
                "url_it": None,
                "url_rm": "invalid-url.ch",
                "name_de": None,
                "name_fr": None,
                "name_en": "English link text",
                "protocol": "WWW:LINK",
            },
        ],
    }
    contact.update(overrides)
    return contact


def _dump(contact: Contact) -> dict:
    return contact.model_dump(exclude_none=True, by_alias=True)


def test_from_legacy_maps_all_fields():
    contact = Contact.from_legacy(_legacy_contact(), lang="fr")

    assert _dump(contact) == {
        "organization": "Office fédéral de topographie swisstopo",
        "position": "Distribution des géodonnées",
        "phones": [
            {"value": "+41 58 469 01 11", "roles": ["work"]},
            {"value": "+41 58 469 04 59", "roles": ["fax"]},
            {"value": "+41 79 123 45 67", "roles": ["sms"]},
        ],
        "emails": [{"value": "geodata@swisstopo.ch"}, {"value": "another@test.ch"}],
        "addresses": [
            {
                "deliveryPoint": ["Seftigenstrasse 264"],
                "city": "Wabern",
                "postalCode": "3084",
                "country": "CH",
            }
        ],
        "links": [{"href": "http://www.swisstopo.ch/fr", "type": "text/html", "hreflang": "fr"}],
        "roles": ["pointOfContact"],
    }


def test_from_legacy_falls_back_to_unlocalized_fields():
    contact = Contact.from_legacy(_legacy_contact(), lang="en")

    assert contact.organization == "Federal Office of Topography swisstopo"
    assert contact.position is None
    # url_en is None, so the unlocalized url is used.
    assert contact.links == [
        UnvalidatedLink(href="http://www.swisstopo.ch", typ="text/html", hreflang=None, title=None),
    ]


def test_from_legacy_sets_country_as_is_even_when_none():
    contact = Contact.from_legacy(_legacy_contact(contact_country=None), lang="de")

    assert contact.addresses[0].country is None


def test_from_legacy_sets_reports_url_even_if_invalid_format():
    contact = Contact.from_legacy(_legacy_contact(), lang="rm")

    assert contact.links == [
        UnvalidatedLink(href="invalid-url.ch", typ="text/html", hreflang="rm", title=None),
    ]


def test_from_legacy_link_skipped_if_no_url():
    legacy_contact = _legacy_contact(lang="de")
    legacy_contact["online_resources"][0]["url"] = None
    legacy_contact["online_resources"][0]["url_de"] = None
    contact = Contact.from_legacy(legacy_contact, lang="de")

    assert not contact.links


def test_from_legacy_returns_none_without_organization():
    """The OGC contact schema requires at least one of `name` or `organization`."""
    legacy_contact = _legacy_contact()
    legacy_contact["org_name"] = None
    legacy_contact["org_name_de"] = None
    legacy_contact["org_name_fr"] = None
    legacy_contact["org_name_it"] = None
    legacy_contact["org_name_rm"] = None
    legacy_contact["org_name_en"] = None

    assert Contact.from_legacy(legacy_contact, lang="de") is None


def test_from_dataset_exports_all_roles(db):
    dataset = Dataset(
        sgid="dat_test",
        dataset_id="ch.swisstopo.test",
        title_de="Test",
        title_fr="Test",
        title_en="Test",
        title_it="Test",
        title_rm="Test",
        description_de="Test",
        description_fr="Test",
        description_en="Test",
        description_it="Test",
        description_rm="Test",
        geocat_id="abcd",
        legacy_contacts=[
            _legacy_contact(role=DatasetToContact.Role.OWNER),
            _legacy_contact(role=DatasetToContact.Role.POINT_OF_CONTACT),
            _legacy_contact(role=DatasetToContact.Role.CUSTODIAN),
        ],
    )
    dataset.save()

    record = OARDataset.from_dataset(dataset, lang="de")

    contacts = record.properties["contacts"]
    assert [contact.roles for contact in contacts] == [
        [DatasetToContact.Role.OWNER],
        [DatasetToContact.Role.POINT_OF_CONTACT],
        [DatasetToContact.Role.CUSTODIAN],
    ]
    assert all(
        contact.organization == "Bundesamt für Landestopografie swisstopo" for contact in contacts
    )


@pytest.mark.parametrize(
    ("short_titles", "lang", "expected"),
    [
        ({"title_short_fr": "Court FR", "title_short_en": "Short EN"}, "fr", "Court FR"),
        ({"title_short_en": "Short EN", "title_short_de": "Kurz DE"}, "fr", "Short EN"),
        ({"title_short_de": "Kurz DE"}, "fr", "Kurz DE"),
        ({}, "fr", "Titre FR"),
        ({}, "rm", "Title EN"),
    ],
)
def test_from_dataset_short_title_fallback(db, short_titles, lang, expected):
    dataset = Dataset(
        sgid="dat_test",
        dataset_id="ch.swisstopo.test",
        title_de="Titel DE",
        title_fr="Titre FR",
        title_en="Title EN",
        geocat_id="abcd",
        **short_titles,
    )
    dataset.save()

    record = OARDataset.from_dataset(dataset, lang=lang)

    assert record.properties["shortTitle"] == expected


@pytest.mark.parametrize(
    "href",
    [
        "/collections/abc/items",
        "/collections/abc/items?limit=10&offset=5",
        "relative/path",
        "?query=only",
        "#fragment",
    ],
)
def test_internal_link_accepts_valid_hrefs(href):
    assert RelativeLink(href=href).href == href


@pytest.mark.parametrize(
    "href",
    [
        "",
        "   ",
        "https://example.com/items",
        "mailto:someone@example.com",
        "//example.com/items",
        "http://[invalid",
    ],
)
def test_internal_link_rejects_invalid_hrefs(href):
    with pytest.raises(ValidationError):
        RelativeLink(href=href)


LEGEND_BASE_URL = "https://api3.geo.admin.ch/static/images/legends/ch.bfe.shared-mobility"


def _geojson_distribution(**legends) -> ExternalGeoJSONDistribution:
    dataset = Dataset(
        sgid="dat_shared-mobility",
        dataset_id="ch.bfe.shared-mobility",
        title_de="Titel DE",
        geocat_id="abcd",
    )
    dataset.save()
    distribution = ExternalGeoJSONDistribution(
        sgid="dst_shared-mobility-123",
        distribution_id="ch.bfe.shared-mobility:geojson",
        dataset=dataset,
        title_de="GeoJSON DE",
        geojson_url_de="https://data.geo.admin.ch/ch.bfe.shared-mobility/shared-mobility_de.json",
        geojson_url_fr="https://data.geo.admin.ch/ch.bfe.shared-mobility/shared-mobility_fr.json",
        **legends,
    )
    distribution.save()
    return distribution


def _legend_links(record: OARDistribution) -> list[dict]:
    return [
        link.model_dump(exclude_none=True, by_alias=True)
        for link in record.links
        if link.rel == "legend"
    ]


def test_from_distribution_exports_geojson_legend_link(db):
    distribution = _geojson_distribution(
        geojson_legend_de=f"{LEGEND_BASE_URL}_de.png",
        geojson_legend_fr=f"{LEGEND_BASE_URL}_fr.png",
    )

    for lang in ("de", "fr"):
        record = OARDistribution.from_distribution(distribution, lang=lang)
        assert _legend_links(record) == [
            {
                "href": f"{LEGEND_BASE_URL}_{lang}.png",
                "rel": "legend",
                "title": "Legend of the GeoJSON layer",
                "type": "image/png",
            }
        ]


def test_from_distribution_skips_missing_geojson_legend_link(db):
    distribution = _geojson_distribution(geojson_legend_de=f"{LEGEND_BASE_URL}_de.png")

    # No legend stored for these languages, so no legend link is exported.
    for lang in ("fr", "it", "en", "rm"):
        record = OARDistribution.from_distribution(distribution, lang=lang)
        assert _legend_links(record) == []
