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
    assert response.status_code == 422
    assert response.json() == {
        "code": 422,
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
