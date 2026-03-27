from unittest.mock import patch

import pytest

from config.authorization import VPRole

# ==========  GET  ==========


@patch("utils.auth._get_vp_client")
@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401), ("user", 403)])
def test_get_human_users_unauthorized(
    vp_client, username, status_code, user_headers, organization, client
):
    vp_client.return_value.is_authorized.return_value = False
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}/users",
        headers=user_headers[username],
    )

    assert response.status_code == status_code
    assert response.status_code == status_code


@pytest.mark.parametrize("username", ["superuser", "organization_admin"])
def test_get_human_users_returns_expected(username, user_headers, user, client):
    response = client.get(
        f"/api/v1/organizations/{user.organization.organization_id}/users",
        headers=user_headers[username],
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "email": "organization_admin@example.org",
                "first_name": "Organization",
                "id": "organization_admin",
                "last_name": "Admin",
                "roles": [],
            },
            {
                "email": "c.n@example.com",
                "first_name": "Chuck",
                "id": "1234",
                "last_name": "Norris",
                "roles": [],
                "unit": {
                    "id": "ch.bafu.fauna",
                    "name": "Fauna",
                    "name_translations": {
                        "de": "Fauna",
                        "en": "Fauna",
                        "fr": "Faune",
                        "it": "Fauna",
                        "rm": "Fauna",
                    },
                    "organization_id": "ch.bafu",
                },
            },
            {
                "email": "organization_user@example.org",
                "first_name": "Organization",
                "id": "organization_user",
                "last_name": "User",
                "roles": [],
            },
        ]
    }


# ==========  PUT  ==========


@patch("utils.auth._get_vp_client")
@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401), ("user", 403)])
def test_update_human_user_unauthorized(
    vp_client, username, status_code, user_headers, user, client
):
    vp_client.return_value.is_authorized.return_value = False
    response = client.put(
        f"/api/v1/organizations/{user.organization.organization_id}/users/{user.sub}",
        content_type="application/json",
        headers=user_headers[username],
        data={"unit_id": "some_unit_id", "roles": []},
    )

    assert response.status_code == status_code


@patch("user.models.Client")
@patch("user.extra_audience.Client")
@patch("utils.auth._get_vp_client")
@pytest.mark.parametrize("username", ["superuser", "organization_admin"])
def test_update_human_user_updates_as_expected(
    vp_client, ssm_client, boto_client, username, user_headers, user, client
):
    response = client.put(
        f"/api/v1/organizations/{user.organization.organization_id}/users/{user.sub}",
        content_type="application/json",
        headers=user_headers[username],
        data={"unit_id": None, "roles": [VPRole.ORG_ADMIN.value]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "id": user.sub,
        "roles": [
            {
                "description": "Organization administrator with full access to all resources.",
                "id": "org_admin",
                "name": "Organization Admin",
            },
        ],
    }
    assert boto_client.return_value.remove_user_from_group.called
    assert boto_client.return_value.update_user_roles.called


# ==========  DELETE  ==========


@patch("utils.auth._get_vp_client")
@pytest.mark.parametrize(("username", "status_code"), [("anonymous", 401), ("user", 403)])
def test_delete_human_user_unauthorized(
    vp_client, username, status_code, user_headers, user, client
):
    vp_client.return_value.is_authorized.return_value = False
    response = client.delete(
        f"/api/v1/organizations/{user.organization.organization_id}/users/{user.sub}",
        headers=user_headers[username],
    )

    assert response.status_code == status_code


@patch("user.models.Client")
@pytest.mark.parametrize("username", ["superuser", "organization_admin"])
def test_delete_human_user_deletes_as_expected(boto_client, username, user_headers, user, client):
    response = client.delete(
        f"/api/v1/organizations/{user.organization.organization_id}/users/{user.sub}",
        headers=user_headers[username],
    )

    assert response.status_code == 204
    assert boto_client.return_value.remove_user_from_group.call_count == 2
    assert boto_client.return_value.update_user_roles.call_count == 1
