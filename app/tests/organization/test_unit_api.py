from unittest.mock import patch

import pytest

from organization.api import unit_to_response
from organization.models import Unit
from organization.schemas import UnitSchema
from schemas import TranslationsSchema


def test_unit_to_response_returns_response_with_language_as_defined(unit):
    actual = unit_to_response(unit, lang="de")

    expected = UnitSchema(
        id="ch.bafu.fauna",
        organization_id="ch.bafu",
        name="Fauna",
        name_translations=TranslationsSchema(
            de="Fauna",
            fr="Faune",
            en="Fauna",
            it="Fauna",
            rm="Fauna",
        ),
    )

    assert actual == expected


def test_unit_to_response_returns_response_with_default_language_if_undefined(
    unit,
):
    unit.name_it = None
    unit.name_rm = None

    actual = unit_to_response(unit, lang="it")

    expected = UnitSchema(
        id="ch.bafu.fauna",
        organization_id="ch.bafu",
        name="Fauna",
        name_translations=TranslationsSchema(
            de="Fauna",
            fr="Faune",
            en="Fauna",
            it=None,
            rm=None,
        ),
    )

    assert actual == expected


# ==========  GET  ==========


@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401), ("user", 403)])
def test_get_unit_unauthorized(username, status_code, user_headers, unit, client):
    response = client.get(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}",
        headers=user_headers[username],
    )

    assert response.status_code == status_code


@pytest.mark.parametrize("username", ["admin", "organization_admin"])
def test_get_unit_returns_existing_with_default_language(username, user_headers, unit, client):
    response = client.get(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}",
        headers=user_headers[username],
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name": "Fauna",
        "name_translations": {
            "de": "Fauna",
            "fr": "Faune",
            "en": "Fauna",
            "it": "Fauna",
            "rm": "Fauna",
        },
    }


def test_get_unit_returns_with_language_from_query(user_headers, unit, client):
    response = client.get(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}?lang=fr",
        headers=user_headers["admin"],
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name": "Faune",
        "name_translations": {
            "de": "Fauna",
            "fr": "Faune",
            "en": "Fauna",
            "it": "Fauna",
            "rm": "Fauna",
        },
    }


def test_get_unit_returns_404_for_nonexisting_organization(user_headers, client, unit):
    response = client.get(
        f"/api/v1/organizations/non_existant/units/{unit.unit_id}",
        headers=user_headers["admin"],
    )

    assert response.status_code == 404
    assert response.json() == {"code": 404, "description": "Resource not found"}

    response = client.get(
        f"/api/v1/organizations/{unit.organization_id}/units/non_existant",
        headers=user_headers["admin"],
    )

    assert response.status_code == 404
    assert response.json() == {"code": 404, "description": "Resource not found"}


def test_get_unit_skips_translations_that_are_not_available(user_headers, unit, client):
    unit = Unit.objects.last()
    unit.name_it = None
    unit.name_rm = None
    unit.acronym_it = None
    unit.acronym_rm = None
    unit.save()

    response = client.get(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}",
        headers=user_headers["admin"],
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name": "Fauna",
        "name_translations": {
            "de": "Fauna",
            "fr": "Faune",
            "en": "Fauna",
        },
    }


def test_get_unit_returns_with_language_from_header(user_headers, unit, client):
    response = client.get(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}",
        headers=user_headers["admin"] | {"Accept-Language": "de"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name": "Fauna",
        "name_translations": {
            "de": "Fauna",
            "fr": "Faune",
            "en": "Fauna",
            "it": "Fauna",
            "rm": "Fauna",
        },
    }


def test_get_unit_returns_with_language_from_query_param_even_if_header_set(
    user_headers, unit, client
):
    response = client.get(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}?lang=fr",
        headers=user_headers["admin"] | {"Accept-Language": "de"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name": "Faune",
        "name_translations": {
            "de": "Fauna",
            "fr": "Faune",
            "en": "Fauna",
            "it": "Fauna",
            "rm": "Fauna",
        },
    }


def test_get_unit_returns_with_default_language_if_header_empty(user_headers, unit, client):
    response = client.get(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}",
        headers=user_headers["admin"] | {"Accept-Language": ""},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name": "Fauna",
        "name_translations": {
            "de": "Fauna",
            "fr": "Faune",
            "en": "Fauna",
            "it": "Fauna",
            "rm": "Fauna",
        },
    }


def test_get_unit_returns_with_first_known_language_from_header(user_headers, unit, client):
    response = client.get(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}",
        headers=user_headers["admin"] | {"Accept-Language": "cn, *, de-DE, en"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name": "Fauna",
        "name_translations": {
            "de": "Fauna",
            "fr": "Faune",
            "en": "Fauna",
            "it": "Fauna",
            "rm": "Fauna",
        },
    }


def test_get_unit_returns_with_first_known_language_from_header_ignoring_qfactor(
    user_headers, unit, client
):
    response = client.get(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}",
        headers=user_headers["admin"] | {"Accept-Language": "fr;q=0.9, de;q=0.8"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name": "Faune",
        "name_translations": {
            "de": "Fauna",
            "fr": "Faune",
            "en": "Fauna",
            "it": "Fauna",
            "rm": "Fauna",
        },
    }


def test_get_units_returns_single_with_given_language(user_headers, unit, client):
    response = client.get(
        f"/api/v1/organizations/{unit.organization.organization_id}/units?lang=fr",
        headers=user_headers["admin"],
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "ch.bafu.fauna",
                "organization_id": "ch.bafu",
                "name": "Faune",
                "name_translations": {
                    "de": "Fauna",
                    "fr": "Faune",
                    "en": "Fauna",
                    "it": "Fauna",
                    "rm": "Fauna",
                },
            }
        ],
    }


def test_get_units_skips_translations_that_are_not_available(user_headers, unit, client):
    unit = Unit.objects.last()
    unit.name_it = None
    unit.name_rm = None
    unit.save()

    response = client.get(
        f"/api/v1/organizations/{unit.organization.organization_id}/units",
        headers=user_headers["admin"],
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "ch.bafu.fauna",
                "organization_id": "ch.bafu",
                "name": "Fauna",
                "name_translations": {
                    "de": "Fauna",
                    "fr": "Faune",
                    "en": "Fauna",
                },
            }
        ],
    }


def test_get_units_returns_with_language_from_header(user_headers, unit, client):
    response = client.get(
        f"/api/v1/organizations/{unit.organization.organization_id}/units",
        headers=user_headers["admin"] | {"Accept-Language": "de"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "ch.bafu.fauna",
                "organization_id": "ch.bafu",
                "name": "Fauna",
                "name_translations": {
                    "de": "Fauna",
                    "fr": "Faune",
                    "en": "Fauna",
                    "it": "Fauna",
                    "rm": "Fauna",
                },
            }
        ],
    }


# ==========  POST  ==========


@patch("organization.models.Client")
@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401), ("user", 403)])
def test_create_unit_unauthorized(
    boto_client, status_code, username, user_headers, client, organization
):
    data = {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name_translations": {
            "de": "Fauna",
            "fr": "Faune",
            "en": "Fauna",
            "it": "Fauna",
            "rm": "Fauna",
        },
    }
    response = client.post(
        "/api/v1/organizations/ch.bafu/units",
        content_type="application/json",
        headers=user_headers[username],
        data=data,
    )

    assert response.status_code == status_code


@patch("organization.models.Client")
@pytest.mark.parametrize("username", ["admin", "organization_admin"])
def test_create_unit_creates_unit_as_expected(
    boto_client, username, user_headers, client, organization
):
    data = {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name_translations": {
            "de": "Fauna",
            "fr": "Faune",
            "en": "Fauna",
            "it": "Fauna",
            "rm": "Fauna",
        },
    }
    response = client.post(
        "/api/v1/organizations/ch.bafu/units",
        content_type="application/json",
        headers=user_headers[username],
        data=data,
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name": "Fauna",
        "name_translations": {
            "de": "Fauna",
            "fr": "Faune",
            "en": "Fauna",
            "it": "Fauna",
            "rm": "Fauna",
        },
    }
    actual = Unit.objects.last()
    assert actual.unit_id == data["id"]
    assert actual.organization.organization_id == data["organization_id"]
    assert actual.name_de == data["name_translations"]["de"]
    assert actual.name_fr == data["name_translations"]["fr"]
    assert actual.name_en == data["name_translations"]["en"]
    assert actual.name_it == data["name_translations"]["it"]
    assert actual.name_rm == data["name_translations"]["rm"]


@patch("organization.models.Client")
def test_create_unit_already_exists(boto_client, user_headers, client, organization):
    data = {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name_translations": {
            "de": "Fauna",
            "fr": "Faune",
            "en": "Fauna",
            "it": "Fauna",
            "rm": "Fauna",
        },
    }
    response = client.post(
        "/api/v1/organizations/ch.bafu/units",
        content_type="application/json",
        headers=user_headers["admin"],
        data=data,
    )
    assert response.status_code == 201

    # Try to create the same organization unit a second time
    response = client.post(
        "/api/v1/organizations/ch.bafu/units",
        content_type="application/json",
        headers=user_headers["admin"],
        data=data,
    )
    assert response.status_code == 409
    assert response.json() == {
        "code": 409,
        "description": ["Unit with this External ID already exists."],
    }


# ==========  PUT  ==========


@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401), ("user", 403)])
def test_update_unit_unauthorized(username, status_code, user_headers, client, unit):
    data = {
        "name_translations": {
            "de": "Name DE",
            "fr": "Name FR",
            "en": "Name EN",
            "it": "Name IT",
            "rm": "Name RM",
        },
    }
    response = client.put(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}",
        content_type="application/json",
        headers=user_headers[username],
        data=data,
    )
    assert response.status_code == status_code


@pytest.mark.parametrize("username", ["admin", "organization_admin"])
def test_update_unit_updates_unit_as_expected(username, user_headers, client, unit):
    data = {
        "name_translations": {
            "de": "Name DE",
            "fr": "Name FR",
            "en": "Name EN",
            "it": "Name IT",
            "rm": "Name RM",
        },
    }
    response = client.put(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}",
        content_type="application/json",
        headers=user_headers[username],
        data=data,
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": "ch.bafu.fauna",
        "organization_id": "ch.bafu",
        "name": "Name EN",
        "name_translations": {
            "de": "Name DE",
            "fr": "Name FR",
            "en": "Name EN",
            "it": "Name IT",
            "rm": "Name RM",
        },
    }
    actual = Unit.objects.last()
    assert actual.name_de == data["name_translations"]["de"]
    assert actual.name_fr == data["name_translations"]["fr"]
    assert actual.name_en == data["name_translations"]["en"]
    assert actual.name_it == data["name_translations"]["it"]
    assert actual.name_rm == data["name_translations"]["rm"]


# ==========  DELETE  ==========


@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401), ("user", 403)])
def test_delete_unit_unauthorized(username, status_code, user_headers, client, unit):
    response = client.delete(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}",
        headers=user_headers[username],
    )
    assert response.status_code == status_code


@pytest.mark.parametrize("username", ["admin", "organization_admin"])
def test_delete_unit_deletes_unit_as_expected(username, user_headers, client, unit):
    response = client.delete(
        f"/api/v1/organizations/{unit.organization.organization_id}/units/{unit.unit_id}",
        headers=user_headers[username],
    )
    assert response.status_code == 204
    assert not Unit.objects.filter(unit_id=unit.unit_id).exists()
