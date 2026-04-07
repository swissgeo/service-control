from unittest.mock import patch

import pytest

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
        ),
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
        ),
    )

    assert actual == expected


# ==========  GET (organization) ==========


@patch("utils.auth._get_vp_client")
@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401), ("user", 403)])
def test_get_organization_unauthorized(
    vp_client, username, status_code, user_headers, organization, client
):
    vp_client.return_value.is_authorized.return_value = False
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}",
        headers=user_headers[username],
    )

    assert response.status_code == status_code


@pytest.mark.parametrize("username", ["superuser", "organization_admin"])
def test_get_organization_returns_existing_organization_with_default_language(
    username, user_headers, organization, client
):
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}",
        headers=user_headers[username],
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
        },
    }


def test_get_organization_returns_organization_with_language_from_query(
    user_headers, organization, client
):
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}?lang=de",
        headers=user_headers["superuser"],
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
        },
    }


def test_get_organization_returns_404_for_nonexisting_organization(user_headers, client, db):
    response = client.get("/api/v1/organizations/2", headers=user_headers["superuser"])

    assert response.status_code == 404
    assert response.json() == {"code": 404, "description": "Resource not found"}


def test_get_organization_skips_translations_that_are_not_available(
    user_headers, organization, client
):
    organization = Organization.objects.last()
    organization.name_it = None
    organization.name_rm = None
    organization.acronym_it = None
    organization.acronym_rm = None
    organization.save()

    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}",
        headers=user_headers["superuser"],
    )

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
        },
    }


def test_get_organization_returns_organization_with_language_from_header(
    user_headers, organization, client
):
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}",
        headers=user_headers["superuser"] | {"Accept-Language": "de"},
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
        },
    }


def test_get_organization_returns_organization_with_language_from_query_param_even_if_header_set(
    user_headers, organization, client
):
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}?lang=fr",
        headers=user_headers["superuser"] | {"Accept-Language": "de"},
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
        },
    }


def test_get_organization_returns_organization_with_default_language_if_header_empty(
    user_headers, organization, client
):
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}",
        headers=user_headers["superuser"] | {"Accept-Language": ""},
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
        },
    }


def test_get_organization_returns_organization_with_first_known_language_from_header(
    user_headers, organization, client
):
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}",
        headers=user_headers["superuser"] | {"Accept-Language": "cn, *, de-DE, en"},
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
        },
    }


def test_get_organization_returns_with_first_known_language_from_header_ignoring_qfactor(
    user_headers, organization, client
):
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}",
        headers=user_headers["superuser"] | {"Accept-Language": "fr;q=0.9, de;q=0.8"},
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
        },
    }


# ==========  GET (organizations)  ==========


@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401)])
def test_get_organizations_unauthorized(username, status_code, user_headers, organization, client):
    response = client.get(
        "/api/v1/organizations?lang=fr",
        headers=user_headers[username],
    )

    assert response.status_code == status_code


@pytest.mark.parametrize(("username"), ["superuser", "user", "organization_admin"])
def test_get_organizations_returns_single_organization_with_given_language(
    username, user_headers, organization, client
):
    response = client.get(
        "/api/v1/organizations?lang=fr",
        headers=user_headers[username],
    )

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
                },
            }
        ],
    }


def test_get_organizations_skips_translations_that_are_not_available(
    user_headers, organization, client
):
    organization = Organization.objects.last()
    organization.name_it = None
    organization.name_rm = None
    organization.acronym_it = None
    organization.acronym_rm = None
    organization.save()

    response = client.get("/api/v1/organizations", headers=user_headers["superuser"])

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
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
                },
            }
        ],
    }


def test_get_organizations_returns_organization_with_language_from_header(
    user_headers, organization, client
):
    response = client.get(
        "/api/v1/organizations", headers=user_headers["superuser"] | {"Accept-Language": "de"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
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
                },
            }
        ],
    }


def test_get_organizations_returns_all_organizations_ordered_by_id_with_given_language(
    user_headers, organization, client
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

    response = client.get("/api/v1/organizations?lang=fr", headers=user_headers["superuser"])

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
                },
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
                },
            },
        ],
    }


# ==========  POST  ==========


@patch("organization.models.Client")
@pytest.mark.parametrize(
    ("username", "status_code"), [("anonymous", 401), ("user", 403), ("organization_admin", 403)]
)
def test_create_organization_unauthorized(
    boto_client, username, status_code, user_headers, client, db
):
    data = {
        "id": "ch.bfs",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFS",
            "en": "FSO",
            "it": "UST",
            "rm": "UST",
        },
        "name_translations": {
            "de": "Bundesamt für Statistik",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Statistical Office",
            "it": "Ufficio federale di statistica",
            "rm": "Uffizi federal da statistica",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers[username],
        data=data,
    )

    assert response.status_code == status_code


@patch("organization.models.Client")
def test_create_organization_creates_organization_as_expected(
    boto_client, user_headers, client, db
):
    data = {
        "id": "ch.bfs",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFS",
            "en": "FSO",
            "it": "UST",
            "rm": "UST",
        },
        "name_translations": {
            "de": "Bundesamt für Statistik",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Statistical Office",
            "it": "Ufficio federale di statistica",
            "rm": "Uffizi federal da statistica",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": "ch.bfs",
        "acronym": "FSO",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFS",
            "en": "FSO",
            "it": "UST",
            "rm": "UST",
        },
        "name": "Federal Statistical Office",
        "name_translations": {
            "de": "Bundesamt für Statistik",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Statistical Office",
            "it": "Ufficio federale di statistica",
            "rm": "Uffizi federal da statistica",
        },
    }
    actual = Organization.objects.last()
    assert actual.organization_id == data["id"]
    assert actual.name_de == data["name_translations"]["de"]
    assert actual.name_fr == data["name_translations"]["fr"]
    assert actual.name_en == data["name_translations"]["en"]
    assert actual.name_it == data["name_translations"]["it"]
    assert actual.name_rm == data["name_translations"]["rm"]

    assert actual.acronym_de == data["acronym_translations"]["de"]
    assert actual.acronym_fr == data["acronym_translations"]["fr"]
    assert actual.acronym_en == data["acronym_translations"]["en"]
    assert actual.acronym_it == data["acronym_translations"]["it"]
    assert actual.acronym_rm == data["acronym_translations"]["rm"]


@patch("organization.models.Client")
def test_create_organization_required_only(boto_client, user_headers, client, db):
    data = {
        "id": "ch.bfs",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFS",
            "en": "FSO",
        },
        "name_translations": {
            "de": "Bundesamt für Statistik",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Statistical Office",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": "ch.bfs",
        "acronym": "FSO",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFS",
            "en": "FSO",
        },
        "name": "Federal Statistical Office",
        "name_translations": {
            "de": "Bundesamt für Statistik",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Statistical Office",
        },
    }


def test_create_organization_missing_required(user_headers, client, db):
    data = {
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
        },
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )
    assert response.status_code == 400
    data = {
        "id": "ch.bafu",
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )
    assert response.status_code == 400
    data = {
        "id": "ch.bafu",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )
    assert response.status_code == 400
    data = {
        "id": "ch.bafu",
        "acronym_translations": {
            "fr": "OFEV",
            "en": "FOEN",
        },
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )
    assert response.status_code == 400
    data = {
        "id": "ch.bafu",
        "acronym_translations": {
            "de": "BAFU",
            "en": "FOEN",
        },
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )
    assert response.status_code == 400
    data = {
        "id": "ch.bafu",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
        },
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )
    assert response.status_code == 400
    data = {
        "id": "ch.bafu",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
        },
        "name_translations": {
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Office for the Environment",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )
    assert response.status_code == 400
    data = {
        "id": "ch.bafu",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
        },
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "en": "Federal Office for the Environment",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )
    assert response.status_code == 400
    data = {
        "id": "ch.bafu",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFEV",
            "en": "FOEN",
        },
        "name_translations": {
            "de": "Bundesamt für Umwelt",
            "fr": "Office fédéral de l'environnement",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )
    assert response.status_code == 400


@patch("organization.models.Client")
def test_create_organization_already_exists(boto_client, user_headers, client, db):
    data = {
        "id": "ch.bfs",
        "acronym_translations": {
            "de": "BAFU",
            "fr": "OFS",
            "en": "FSO",
            "it": "UST",
            "rm": "UST",
        },
        "name_translations": {
            "de": "Bundesamt für Statistik",
            "fr": "Office fédéral de l'environnement",
            "en": "Federal Statistical Office",
            "it": "Ufficio federale di statistica",
            "rm": "Uffizi federal da statistica",
        },
    }
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )
    assert response.status_code == 201

    # Try to create the same organization a second time
    response = client.post(
        "/api/v1/organizations",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )
    assert response.status_code == 409
    assert response.json() == {
        "code": 409,
        "description": ["Organization with this External ID already exists."],
    }


# ==========  PUT  ==========


@patch("utils.auth._get_vp_client")
@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401), ("user", 403)])
def test_update_organization_unauthorized(
    vp_client, username, status_code, user_headers, client, organization
):
    vp_client.return_value.is_authorized.return_value = False
    data = {
        "acronym_translations": {
            "de": "New DE",
            "fr": "New FR",
            "en": "New EN",
            "it": "New IT",
            "rm": "New RM",
        },
        "name_translations": {
            "de": "Name DE",
            "fr": "Name FR",
            "en": "Name EN",
            "it": "Name IT",
            "rm": "Name RM",
        },
    }
    response = client.put(
        f"/api/v1/organizations/{organization.organization_id}",
        content_type="application/json",
        headers=user_headers[username],
        data=data,
    )
    assert response.status_code == status_code


@pytest.mark.parametrize("username", ["superuser", "organization_admin"])
def test_update_organization_updates_organization_as_expected(
    client, username, user_headers, organization
):
    data = {
        "acronym_translations": {
            "de": "New DE",
            "fr": "New FR",
            "en": "New EN",
            "it": "New IT",
            "rm": "New RM",
        },
        "name_translations": {
            "de": "Name DE",
            "fr": "Name FR",
            "en": "Name EN",
            "it": "Name IT",
            "rm": "Name RM",
        },
    }
    response = client.put(
        f"/api/v1/organizations/{organization.organization_id}",
        content_type="application/json",
        headers=user_headers[username],
        data=data,
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu",
        "name": "Name EN",
        "name_translations": {
            "de": "Name DE",
            "fr": "Name FR",
            "en": "Name EN",
            "it": "Name IT",
            "rm": "Name RM",
        },
        "acronym": "New EN",
        "acronym_translations": {
            "de": "New DE",
            "fr": "New FR",
            "en": "New EN",
            "it": "New IT",
            "rm": "New RM",
        },
    }
    actual = Organization.objects.last()
    assert actual.name_de == data["name_translations"]["de"]
    assert actual.name_fr == data["name_translations"]["fr"]
    assert actual.name_en == data["name_translations"]["en"]
    assert actual.name_it == data["name_translations"]["it"]
    assert actual.name_rm == data["name_translations"]["rm"]

    assert actual.acronym_de == data["acronym_translations"]["de"]
    assert actual.acronym_fr == data["acronym_translations"]["fr"]
    assert actual.acronym_en == data["acronym_translations"]["en"]
    assert actual.acronym_it == data["acronym_translations"]["it"]
    assert actual.acronym_rm == data["acronym_translations"]["rm"]


def test_update_organization_not_found(user_headers, client, organization):
    data = {
        "acronym_translations": {
            "de": "New DE",
            "fr": "New FR",
            "en": "New EN",
            "it": "New IT",
            "rm": "New RM",
        },
        "name_translations": {
            "de": "Name DE",
            "fr": "Name FR",
            "en": "Name EN",
            "it": "Name IT",
            "rm": "Name RM",
        },
    }
    response = client.put(
        "/api/v1/organizations/new.id",
        content_type="application/json",
        headers=user_headers["superuser"],
        data=data,
    )
    assert response.status_code == 404
