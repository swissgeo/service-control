import pytest


@pytest.mark.parametrize("username", ["admin", "organization_admin"])
def test_get_roles_returns_expected(username, client, user_headers):
    response = client.get("/api/v1/roles", headers=user_headers[username])

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "dataset_admin",
                "name": "Dataset Admin",
                "description": "Dataset administrator with full access to all datasets of their Unit.",  # noqa: E501
            },
            {
                "id": "dataset_contributor",
                "name": "Dataset Contributor",
                "description": "Dataset contributor with limited access to datasets of their Unit.",
            },
            {
                "id": "org_admin",
                "name": "Organization Admin",
                "description": "Organization administrator with full access to all resources.",
            },
        ]
    }
