from unittest.mock import patch

from organization.api import organization_unit_to_response
from organization.models import OrganizationUnit
from organization.schemas import OrganizationUnitSchema
from schemas import TranslationsSchema


def test_organization_unit_to_response_returns_response_with_language_as_defined(organization_unit):
    actual = organization_unit_to_response(organization_unit, lang="de")

    expected = OrganizationUnitSchema(
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


def test_organization_unit_to_response_returns_response_with_default_language_if_undefined(
    organization_unit,
):
    organization_unit.name_it = None
    organization_unit.name_rm = None

    actual = organization_unit_to_response(organization_unit, lang="it")

    expected = OrganizationUnitSchema(
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


def test_get_organization_unit_returns_existing_with_default_language(organization_unit, client):
    response = client.get(
        f"/api/v1/organizations/{organization_unit.organization.organization_id}/orgunits/{organization_unit.organization_unit_id}"
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


def test_get_organization_unit_returns_with_language_from_query(organization_unit, client):
    response = client.get(
        f"/api/v1/organizations/{organization_unit.organization.organization_id}/orgunits/{organization_unit.organization_unit_id}?lang=fr"
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


def test_get_organization_unit_returns_404_for_nonexisting_organization(client, organization_unit):
    response = client.get(
        f"/api/v1/organizations/non_existant/orgunits/{organization_unit.organization_unit_id}"
    )

    assert response.status_code == 404
    assert response.json() == {"code": 404, "description": "Resource not found"}

    response = client.get(
        f"/api/v1/organizations/{organization_unit.organization_id}/orgunits/non_existant"
    )

    assert response.status_code == 404
    assert response.json() == {"code": 404, "description": "Resource not found"}


def test_get_organization_unit_skips_translations_that_are_not_available(organization_unit, client):
    org_unit = OrganizationUnit.objects.last()
    org_unit.name_it = None
    org_unit.name_rm = None
    org_unit.acronym_it = None
    org_unit.acronym_rm = None
    org_unit.save()

    response = client.get(
        f"/api/v1/organizations/{org_unit.organization.organization_id}/orgunits/{org_unit.organization_unit_id}"
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


def test_get_organization_unit_returns_with_language_from_header(organization_unit, client):
    response = client.get(
        f"/api/v1/organizations/{organization_unit.organization.organization_id}/orgunits/{organization_unit.organization_unit_id}",
        headers={"Accept-Language": "de"},
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


def test_get_organization_unit_returns_with_language_from_query_param_even_if_header_set(
    organization_unit,
    client,
):
    response = client.get(
        f"/api/v1/organizations/{organization_unit.organization.organization_id}/orgunits/{organization_unit.organization_unit_id}?lang=fr",
        headers={"Accept-Language": "de"},
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


def test_get_organization_unit_returns_with_default_language_if_header_empty(
    organization_unit,
    client,
):
    response = client.get(
        f"/api/v1/organizations/{organization_unit.organization.organization_id}/orgunits/{organization_unit.organization_unit_id}",
        headers={"Accept-Language": ""},
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


def test_get_organization_unit_returns_with_first_known_language_from_header(
    organization_unit,
    client,
):
    response = client.get(
        f"/api/v1/organizations/{organization_unit.organization.organization_id}/orgunits/{organization_unit.organization_unit_id}",
        headers={"Accept-Language": "cn, *, de-DE, en"},
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


def test_get_organization_unit_returns_with_first_known_language_from_header_ignoring_qfactor(
    organization_unit,
    client,
):
    response = client.get(
        f"/api/v1/organizations/{organization_unit.organization.organization_id}/orgunits/{organization_unit.organization_unit_id}",
        headers={"Accept-Language": "fr;q=0.9, de;q=0.8"},
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


# def test_get_organization_returns_401_if_not_logged_in(organization, client):
#     response = client.get(f"/api/v1/organizations/{organization.organization_id}")

#     assert response.status_code == 401
#     assert response.json() == {"code": 401, "description": "Unauthorized"}

# def test_get_organization_returns_403_if_no_permission(organization, client, django_user_factory):
#     django_user_factory('test', 'test', [])

#     response = client.get(f"/api/v1/organizations/{organization.organization_id}")

#     assert response.status_code == 403
#     assert response.json() == {"code": 403, "description": "Forbidden"}


def test_get_organization_units_returns_single_with_given_language(organization_unit, client):
    response = client.get(
        f"/api/v1/organizations/{organization_unit.organization.organization_id}/orgunits?lang=fr"
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


def test_get_organization_units_skips_translations_that_are_not_available(
    organization_unit, client
):
    org_unit = OrganizationUnit.objects.last()
    org_unit.name_it = None
    org_unit.name_rm = None
    org_unit.save()

    response = client.get(f"/api/v1/organizations/{org_unit.organization.organization_id}/orgunits")

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


def test_get_organization_units_returns_with_language_from_header(organization_unit, client):
    response = client.get(
        f"/api/v1/organizations/{organization_unit.organization.organization_id}/orgunits",
        headers={"Accept-Language": "de"},
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


@patch("organization.models.Client")
def test_create_organization_unit(boto_client, client, organization):
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
        "/api/v1/organizations/ch.bafu/orgunits", content_type="application/json", data=data
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
    actual = OrganizationUnit.objects.last()
    assert actual.organization_unit_id == data["id"]
    assert actual.organization.organization_id == data["organization_id"]
    assert actual.name_de == data["name_translations"]["de"]
    assert actual.name_fr == data["name_translations"]["fr"]
    assert actual.name_en == data["name_translations"]["en"]
    assert actual.name_it == data["name_translations"]["it"]
    assert actual.name_rm == data["name_translations"]["rm"]


@patch("organization.models.Client")
def test_create_organization_unit_already_exists(boto_client, client, organization):
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
        "/api/v1/organizations/ch.bafu/orgunits", content_type="application/json", data=data
    )
    assert response.status_code == 201

    # Try to create the same organization unit a second time
    response = client.post(
        "/api/v1/organizations/ch.bafu/orgunits", content_type="application/json", data=data
    )
    assert response.status_code == 409
    assert response.json() == {
        "code": 409,
        "description": ["Organization unit with this External ID already exists."],
    }


def test_update_organization_unit(client, organization_unit):
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
        f"/api/v1/organizations/{organization_unit.organization.organization_id}/orgunits/{organization_unit.organization_unit_id}",
        content_type="application/json",
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
    actual = OrganizationUnit.objects.last()
    assert actual.name_de == data["name_translations"]["de"]
    assert actual.name_fr == data["name_translations"]["fr"]
    assert actual.name_en == data["name_translations"]["en"]
    assert actual.name_it == data["name_translations"]["it"]
    assert actual.name_rm == data["name_translations"]["rm"]


def test_delete_organization_unit(client, organization_unit):
    response = client.delete(
        f"/api/v1/organizations/{organization_unit.organization.organization_id}/orgunits/{organization_unit.organization_unit_id}",
    )
    assert response.status_code == 204
    assert not OrganizationUnit.objects.filter(
        organization_unit_id=organization_unit.organization_unit_id
    ).exists()
