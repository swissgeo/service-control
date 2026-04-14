from unittest.mock import patch

from user.models import AccessRequest


def test_create_access_request_unauthorized(organization, client, user_headers):
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["anonymous"],
    )
    assert response.status_code == 401


def test_create_access_request_for_user_who_belongs_to_organization(
    organization, user, client, user_headers
):
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user"],
    )
    assert response.status_code == 409
    assert response.json() == {
        "code": 409,
        "description": "User already belongs to an organization",
    }


def test_create_access_request_for_user_who_already_has_pending_access_request(
    organization, user_without_org, client, user_headers
):
    # Create initial access request for the user
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 201

    # Try to create another access request for the same user while the first one is still pending
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 409
    assert response.json() == {
        "code": 409,
        "description": "User already has a pending access request",
    }


def test_create_access_request_success(organization, user_without_org, client, user_headers):
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],  # check id is returned
        "organization_id": organization.organization_id,
        "organization_acronym": organization.acronym_en,
        "organization_name": organization.name_en,
        "state": "PENDING",
        "created": response.json()["created"],  # check timestamp is returned
    }


def test_list_access_requests_unauthorized(client, user_headers):
    response = client.get("/api/v1/accessrequests", headers=user_headers["anonymous"])
    assert response.status_code == 401


def test_list_access_requests_for_user_without_org(
    organization, user_without_org, client, user_headers
):
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 201

    response = client.get("/api/v1/accessrequests", headers=user_headers["user_without_org"])
    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": response.json()["items"][0]["id"],  # check id is returned
                "organization_id": organization.organization_id,
                "organization_acronym": organization.acronym_en,
                "organization_name": organization.name_en,
                "state": "PENDING",
                "created": response.json()["items"][0]["created"],  # check timestamp is returned
            }
        ],
    }


def test_cancel_access_request(organization, user_without_org, client, user_headers):
    # Create access request
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 201
    access_request_id = response.json()["id"]

    # Cancel access request
    response = client.put(
        f"/api/v1/accessrequests/{access_request_id}",
        content_type="application/json",
        data={"state": "CANCELLED"},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": access_request_id,
        "organization_id": organization.organization_id,
        "organization_acronym": organization.acronym_en,
        "organization_name": organization.name_en,
        "state": "CANCELLED",
        "created": response.json()["created"],  # check timestamp is returned
    }

    # Verify access request is cancelled
    response = client.get("/api/v1/accessrequests", headers=user_headers["user_without_org"])
    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": access_request_id,
                "organization_id": organization.organization_id,
                "organization_acronym": organization.acronym_en,
                "organization_name": organization.name_en,
                "state": "CANCELLED",
                "created": response.json()["items"][0]["created"],  # check timestamp is returned
            }
        ]
    }


def test_cancel_access_request_wrong_state(organization, user_without_org, client, user_headers):
    # Create access request
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 201
    access_request_id = response.json()["id"]

    # Cancel access request
    response = client.put(
        f"/api/v1/accessrequests/{access_request_id}",
        content_type="application/json",
        data={"state": "APPROVED"},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 400
    assert response.json() == {
        "code": 400,
        "description": ["Can only update state to cancelled"],
    }

    # Verify access request is not cancelled
    response = client.get("/api/v1/accessrequests", headers=user_headers["user_without_org"])
    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": access_request_id,
                "organization_id": organization.organization_id,
                "organization_acronym": organization.acronym_en,
                "organization_name": organization.name_en,
                "state": "PENDING",
                "created": response.json()["items"][0]["created"],  # check timestamp is returned
            }
        ]
    }


def test_list_access_requests_for_org_admin(organization, user_without_org, client, user_headers):
    # Create access request for user without org
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 201
    access_request_id = response.json()["id"]

    # List access requests as org admin
    response = client.get(
        f"/api/v1/organizations/{organization.organization_id}/accessrequests",
        headers=user_headers["organization_admin"],
    )
    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": access_request_id,
                "organization_id": organization.organization_id,
                "organization_acronym": organization.acronym_en,
                "organization_name": organization.name_en,
                "state": "PENDING",
                "created": response.json()["items"][0]["created"],  # check timestamp is returned
                "user": {
                    "id": user_without_org.sub,
                    "email": user_without_org.email,
                    "first_name": user_without_org.first_name,
                    "last_name": user_without_org.last_name,
                    "roles": [],  # no roles since user doesn't belong to org yet
                },
            }
        ]
    }


def test_decline_access_request(organization, user_without_org, client, user_headers):
    # Create access request
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 201
    access_request_id = response.json()["id"]

    # Decline access request as org admin
    response = client.put(
        f"/api/v1/organizations/{organization.organization_id}/accessrequests/{access_request_id}",
        content_type="application/json",
        data={"state": "DECLINED", "roles": [], "unit_id": None},
        headers=user_headers["organization_admin"],
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": access_request_id,
        "organization_id": organization.organization_id,
        "organization_acronym": organization.acronym_en,
        "organization_name": organization.name_en,
        "state": "DECLINED",
        "created": response.json()["created"],  # check timestamp is returned
        "user": {
            "id": user_without_org.sub,
            "email": user_without_org.email,
            "first_name": user_without_org.first_name,
            "last_name": user_without_org.last_name,
            "roles": [],  # no roles since access request was declined
        },
    }

    # Verify access request is declined
    access_request = AccessRequest.objects.get(access_request_id=access_request_id)
    assert access_request.state == "DECLINED"
    user_without_org.refresh_from_db()
    assert user_without_org.organization is None
    assert user_without_org.roles == []
    assert user_without_org.unit is None


@patch("user.models.Client")
def test_approve_access_request(
    mock_client, organization, unit, user_without_org, client, user_headers
):
    # Create access request
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 201
    access_request_id = response.json()["id"]

    # Approve access request as org admin
    response = client.put(
        f"/api/v1/organizations/{organization.organization_id}/accessrequests/{access_request_id}",
        content_type="application/json",
        data={"state": "APPROVED", "roles": ["dataset_contributor"], "unit_id": unit.unit_id},
        headers=user_headers["organization_admin"],
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": access_request_id,
        "organization_id": organization.organization_id,
        "organization_acronym": organization.acronym_en,
        "organization_name": organization.name_en,
        "state": "APPROVED",
        "created": response.json()["created"],  # check timestamp is returned
        "user": {
            "id": user_without_org.sub,
            "email": user_without_org.email,
            "first_name": user_without_org.first_name,
            "last_name": user_without_org.last_name,
            "roles": [
                {
                    "id": "dataset_contributor",
                    "name": "Dataset Contributor",
                    "description": (
                        "Dataset contributor with limited access to datasets of their Unit."
                    ),
                }
            ],
            "unit": {
                "id": unit.unit_id,
                "name": unit.name_en,
                "name_translations": {
                    "de": unit.name_de,
                    "fr": unit.name_fr,
                    "en": unit.name_en,
                    "it": unit.name_it,
                    "rm": unit.name_rm,
                },
                "organization_id": unit.organization.organization_id,
            },
        },
    }

    # Verify access request is approved and user is added to organization with correct role
    access_request = AccessRequest.objects.get(access_request_id=access_request_id)
    assert access_request.state == "APPROVED"
    user_without_org.refresh_from_db()
    assert user_without_org.organization.organization_id == organization.organization_id
    assert user_without_org.roles == ["dataset_contributor"]
    assert user_without_org.unit.unit_id == unit.unit_id


@patch("user.models.Client")
def test_approve_access_request_status_not_pending(
    mock_client, organization, unit, user_without_org, client, user_headers
):
    # Create access request
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 201
    access_request_id = response.json()["id"]

    # Approve access request as org admin
    response = client.put(
        f"/api/v1/organizations/{organization.organization_id}/accessrequests/{access_request_id}",
        content_type="application/json",
        data={"state": "APPROVED", "roles": ["dataset_contributor"], "unit_id": unit.unit_id},
        headers=user_headers["organization_admin"],
    )
    assert response.status_code == 200

    # Try to approve access request without pending status
    response = client.put(
        f"/api/v1/organizations/{organization.organization_id}/accessrequests/{access_request_id}",
        content_type="application/json",
        data={"state": "APPROVED", "roles": ["dataset_contributor"], "unit_id": unit.unit_id},
        headers=user_headers["organization_admin"],
    )
    assert response.status_code == 409
    assert response.json() == {
        "code": 409,
        "description": "Only pending access requests can be updated",
    }


def test_approve_access_request_to_bad_status(
    organization, unit, user_without_org, client, user_headers
):
    # Create access request
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 201
    access_request_id = response.json()["id"]

    # Approve access request as org admin
    response = client.put(
        f"/api/v1/organizations/{organization.organization_id}/accessrequests/{access_request_id}",
        content_type="application/json",
        data={"state": "PENDING", "roles": ["dataset_contributor"], "unit_id": unit.unit_id},
        headers=user_headers["organization_admin"],
    )
    assert response.status_code == 400
    assert response.json() == {
        "code": 400,
        "description": ["Can only update state to approved or declined"],
    }

    # Try to approve access request without pending status
    response = client.put(
        f"/api/v1/organizations/{organization.organization_id}/accessrequests/{access_request_id}",
        content_type="application/json",
        data={"state": "CANCELLED", "roles": ["dataset_contributor"], "unit_id": unit.unit_id},
        headers=user_headers["organization_admin"],
    )
    assert response.status_code == 400
    assert response.json() == {
        "code": 400,
        "description": ["Can only update state to approved or declined"],
    }


def test_approve_access_request_without_roles(
    organization, unit, user_without_org, client, user_headers
):
    # Create access request
    response = client.post(
        "/api/v1/accessrequests",
        content_type="application/json",
        data={"organization_id": organization.organization_id},
        headers=user_headers["user_without_org"],
    )
    assert response.status_code == 201
    access_request_id = response.json()["id"]

    # Approve access request as org admin
    response = client.put(
        f"/api/v1/organizations/{organization.organization_id}/accessrequests/{access_request_id}",
        content_type="application/json",
        data={"state": "APPROVED", "roles": [], "unit_id": unit.unit_id},
        headers=user_headers["organization_admin"],
    )
    assert response.status_code == 400
    assert response.json() == {
        "code": 400,
        "description": ["At least 1 role must be assigned when approving an access request"],
    }
