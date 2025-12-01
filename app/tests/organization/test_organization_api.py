from organization.api import organization_to_response
from organization.models import Organization
from organization.schemas import OrganizationSchema
from schemas import TranslationsSchema


def test_organization_to_response_returns_response_with_language_as_defined(organization):
    actual = organization_to_response(organization, lang="de")

    expected = OrganizationSchema(
        id="ch.bafu",
        name="Bundesamt für Umwelt",
        name_translations=TranslationsSchema(
            de="Bundesamt für Umwelt",
            fr="Office fédéral de l'environnement",
            en="Federal Office for the Environment",
            it="Ufficio federale dell'ambiente",
            rm="Uffizi federal per l'ambient",
        ),
        acronym="BAFU",
        acronym_translations=TranslationsSchema(
            de="BAFU",
            fr="OFEV",
            en="FOEN",
            it="UFAM",
            rm="UFAM",
        )
    )

    assert actual == expected


def test_organization_to_response_returns_response_with_default_language_if_undefined(organization):
    organization.name_it = None
    organization.name_rm = None
    organization.acronym_it = None
    organization.acronym_rm = None

    actual = organization_to_response(organization, lang="it")

    expected = OrganizationSchema(
        id="ch.bafu",
        name="Federal Office for the Environment",
        name_translations=TranslationsSchema(
            de="Bundesamt für Umwelt",
            fr="Office fédéral de l'environnement",
            en="Federal Office for the Environment",
            it=None,
            rm=None,
        ),
        acronym="FOEN",
        acronym_translations=TranslationsSchema(
            de="BAFU",
            fr="OFEV",
            en="FOEN",
            it=None,
            rm=None,
        )
    )

    assert actual == expected


def test_get_organization_returns_existing_organization_with_default_language(organization, client):
    client.login(username='test', password='test')

    response = client.get(f"/api/v1/organizations/{organization.organization_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu",
        "name": "Federal Office for the Environment",
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
            "it": "Ufficio federale dell'ambiente",
            "rm": "Uffizi federal per l'ambient",
        },
        "acronym": "FOEN",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
            "it": "UFAM",
            "rm": "UFAM",
        }
    }


def test_get_organization_returns_organization_with_language_from_query(organization, client):
    client.login(username='test', password='test')

    response = client.get(f"/api/v1/organizations/{organization.organization_id}?lang=de")

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu",
        "name": "Bundesamt für Umwelt",
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
            "it": "Ufficio federale dell'ambiente",
            "rm": "Uffizi federal per l'ambient",
        },
        "acronym": "BAFU",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
            "it": "UFAM",
            "rm": "UFAM",
        }
    }


def test_get_organization_returns_404_for_nonexisting_organization(client, db):

    response = client.get("/api/v1/organizations/2")

    assert response.status_code == 404
    assert response.json() == {"code": 404, "description": "Resource not found"}


def test_get_organization_skips_translations_that_are_not_available(organization, client):

    organization = Organization.objects.last()
    organization.name_it = None
    organization.name_rm = None
    organization.acronym_it = None
    organization.acronym_rm = None
    organization.save()

    response = client.get(f"/api/v1/organizations/{organization.organization_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu",
        "name": "Federal Office for the Environment",
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
        },
        "acronym": "FOEN",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
        }
    }


def test_get_organization_returns_organization_with_language_from_header(organization, client):

    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}", headers={"Accept-Language": "de"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu",
        "name": "Bundesamt für Umwelt",
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
            "it": "Ufficio federale dell'ambiente",
            "rm": "Uffizi federal per l'ambient",
        },
        "acronym": "BAFU",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
            "it": "UFAM",
            "rm": "UFAM",
        }
    }


def test_get_organization_returns_organization_with_language_from_query_param_even_if_header_set(
    organization, client
):
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}?lang=fr",
        headers={"Accept-Language": "de"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu",
        "name": "Office fédéral de l'environnement",
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
            "it": "Ufficio federale dell'ambiente",
            "rm": "Uffizi federal per l'ambient",
        },
        "acronym": "OFEV",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
            "it": "UFAM",
            "rm": "UFAM",
        }
    }


def test_get_organization_returns_organization_with_default_language_if_header_empty(
    organization, client
):
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}", headers={"Accept-Language": ""}
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu",
        "name": "Federal Office for the Environment",
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
            "it": "Ufficio federale dell'ambiente",
            "rm": "Uffizi federal per l'ambient",
        },
        "acronym": "FOEN",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
            "it": "UFAM",
            "rm": "UFAM",
        }
    }


def test_get_organization_returns_organization_with_first_known_language_from_header(
    organization, client
):
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}",
        headers={"Accept-Language": "cn, *, de-DE, en"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu",
        "name": "Bundesamt für Umwelt",
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
            "it": "Ufficio federale dell'ambiente",
            "rm": "Uffizi federal per l'ambient",
        },
        "acronym": "BAFU",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
            "it": "UFAM",
            "rm": "UFAM",
        }
    }


def test_get_organization_returns_with_first_known_language_from_header_ignoring_qfactor(
    organization, client
):
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}",
        headers={"Accept-Language": "fr;q=0.9, de;q=0.8"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu",
        "name": "Office fédéral de l'environnement",
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
            "it": "Ufficio federale dell'ambiente",
            "rm": "Uffizi federal per l'ambient",
        },
        "acronym": "OFEV",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
            "it": "UFAM",
            "rm": "UFAM",
        }
    }


# def test_get_organization_returns_401_if_not_logged_in(organization, client):
#     response = client.get(f"/api/v1/organizations/{organization.organization_id}")

#     assert response.status_code == 401
#     assert response.json() == {"code": 401, "description": "Unauthorized"}

# def test_get_organization_returns_403_if_no_permission(organization, client, django_user_factory):
#     django_user_factory('test', 'test', [])

#     response = client.get(f"/api/v1/organizations/{organization.organization_id}")

#     assert response.status_code == 403
#     assert response.json() == {"code": 403, "description": "Forbidden"}


def test_get_organizations_returns_single_organization_with_given_language(organization, client):
    response = client.get("/api/v1/organizations?lang=fr")

    assert response.status_code == 200
    assert response.json() == {
        "items": [{
            "id": "ch.bafu",
            "name": "Office fédéral de l'environnement",
            "name_translations": {
                "de": "Bundesamt für Umwelt",
                "fr": "Office fédéral de l'environnement",
                "en": "Federal Office for the Environment",
                "it": "Ufficio federale dell'ambiente",
                "rm": "Uffizi federal per l'ambient",
            },
            "acronym": "OFEV",
            "acronym_translations": {
                "de": "BAFU",
                "fr": "OFEV",
                "en": "FOEN",
                "it": "UFAM",
                "rm": "UFAM",
            }
        }]
    }


def test_get_organizations_skips_translations_that_are_not_available(organization, client):
    organization = Organization.objects.last()
    organization.name_it = None
    organization.name_rm = None
    organization.acronym_it = None
    organization.acronym_rm = None
    organization.save()

    response = client.get("/api/v1/organizations")

    assert response.status_code == 200
    assert response.json() == {
        "items": [{
            "id": "ch.bafu",
            "name": "Federal Office for the Environment",
            "name_translations": {
                "de": "Bundesamt für Umwelt",
                "fr": "Office fédéral de l'environnement",
                "en": "Federal Office for the Environment",
            },
            "acronym": "FOEN",
            "acronym_translations": {
                "de": "BAFU",
                "fr": "OFEV",
                "en": "FOEN",
            }
        }]
    }


def test_get_organizations_returns_organization_with_language_from_header(organization, client):
    response = client.get("/api/v1/organizations", headers={"Accept-Language": "de"})

    assert response.status_code == 200
    assert response.json() == {
        "items": [{
            "id": "ch.bafu",
            "name": "Bundesamt für Umwelt",
            "name_translations": {
                "de": "Bundesamt für Umwelt",
                "fr": "Office fédéral de l'environnement",
                "en": "Federal Office for the Environment",
                "it": "Ufficio federale dell'ambiente",
                "rm": "Uffizi federal per l'ambient",
            },
            "acronym": "BAFU",
            "acronym_translations": {
                "de": "BAFU",
                "fr": "OFEV",
                "en": "FOEN",
                "it": "UFAM",
                "rm": "UFAM",
            }
        }]
    }


def test_get_organizations_returns_all_organizations_ordered_by_id_with_given_language(
    organization, client
):
    organization = {
        "organization_id": "ch.bav",
        "name_de": "Bundesamt für Verkehr",
        "name_fr": "Office fédéral des transports",
        "name_en": "Federal Office of Transport",
        "name_it": "Ufficio federale dei trasporti",
        "name_rm": "Uffizi federal da traffic",
        "acronym_de": "BAV",
        "acronym_fr": "OFT",
        "acronym_en": "FOT",
        "acronym_it": "UFT",
        "acronym_rm": "UFT",
    }
    Organization.objects.create(**organization)

    response = client.get("/api/v1/organizations?lang=fr")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "ch.bafu",
                "name": "Office fédéral de l'environnement",
                "name_translations": {
                    "de": "Bundesamt für Umwelt",
                    "fr": "Office fédéral de l'environnement",
                    "en": "Federal Office for the Environment",
                    "it": "Ufficio federale dell'ambiente",
                    "rm": "Uffizi federal per l'ambient",
                },
                "acronym": "OFEV",
                "acronym_translations": {
                    "de": "BAFU",
                    "fr": "OFEV",
                    "en": "FOEN",
                    "it": "UFAM",
                    "rm": "UFAM",
                }
            },
            {
                "id": "ch.bav",
                "name": "Office fédéral des transports",
                "name_translations": {
                    "de": "Bundesamt für Verkehr",
                    "fr": "Office fédéral des transports",
                    "en": "Federal Office of Transport",
                    "it": "Ufficio federale dei trasporti",
                    "rm": "Uffizi federal da traffic",
                },
                "acronym": "OFT",
                "acronym_translations": {
                    "de": "BAV",
                    "fr": "OFT",
                    "en": "FOT",
                    "it": "UFT",
                    "rm": "UFT",
                }
            },
        ]
    }
