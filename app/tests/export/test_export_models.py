from dataset.models import Dataset, DatasetToContact
from oar_export.export_models import Contact, OARDataset


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
        "contact_electronic_mail_addresses": ["geodata@swisstopo.ch"],
        "online_resources": [
            {
                "url": "http://www.swisstopo.ch",
                "url_de": "http://www.swisstopo.ch",
                "url_fr": "http://www.swisstopo.ch/fr",
                "url_en": None,
                "url_it": None,
                "url_rm": None,
                "name_de": None,
                "name_fr": None,
                "protocol": "WWW:LINK",
            },
            {
                "url": "invalid-url.ch",
                "url_de": "invalid-url.ch",
                "url_fr": "invalid-url.ch",
                "url_en": None,
                "url_it": None,
                "url_rm": None,
                "name_de": None,
                "name_fr": None,
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
        "emails": [{"value": "geodata@swisstopo.ch"}],
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
    assert [(link.href, link.hreflang) for link in contact.links] == [
        ("http://www.swisstopo.ch", "en")
    ]


def test_from_legacy_defaults_country_to_ch():
    contact = Contact.from_legacy(_legacy_contact(contact_country=None), lang="de")

    assert contact.addresses[0].country == "CH"


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
        dataset_id="ch.swisstopo.test",
        title_short_de="Test",
        title_short_fr="Test",
        title_short_en="Test",
        title_short_it="Test",
        title_short_rm="Test",
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
