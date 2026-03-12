from django.http import HttpRequest

from utils.api_path import Parameter


def test_parameter_vp_entity():
    request = HttpRequest()
    request.resolver_match = type("ResolverMatch", (), {"kwargs": {"organization_id": "org123"}})()

    result = Parameter.ORGANIZATION.vp_entity(request, "test_namespace")

    assert result == {
        "entityType": "test_namespace::Organization",
        "entityId": "org123",
    }

    request.resolver_match = type(
        "ResolverMatch", (), {"kwargs": {"organization_id": "org123", "unit_id": "unit123"}}
    )()

    result = Parameter.UNIT.vp_entity(request, "test_namespace")

    assert result == {
        "entityType": "test_namespace::Unit",
        "entityId": "unit123",
    }

    request.resolver_match = type(
        "ResolverMatch",
        (),
        {"kwargs": {"organization_id": "org123", "machine_user_id": "machine123"}},
    )()

    result = Parameter.MACHINE_USER.vp_entity(request, "test_namespace")

    assert result == {
        "entityType": "test_namespace::MachineUser",
        "entityId": "machine123",
    }


def test_parameter_vp_entity_with_parents():
    request = HttpRequest()
    request.resolver_match = type("ResolverMatch", (), {"kwargs": {"organization_id": "org123"}})()

    result = Parameter.ORGANIZATION.vp_entity_with_parents(request, "test_namespace")

    assert result == {
        "identifier": {
            "entityType": "test_namespace::Organization",
            "entityId": "org123",
        },
        "parents": [],
    }

    request.resolver_match = type(
        "ResolverMatch", (), {"kwargs": {"organization_id": "org123", "unit_id": "unit123"}}
    )()

    result = Parameter.UNIT.vp_entity_with_parents(request, "test_namespace")

    assert result == {
        "identifier": {
            "entityType": "test_namespace::Unit",
            "entityId": "unit123",
        },
        "parents": [
            {
                "entityType": "test_namespace::Organization",
                "entityId": "org123",
            }
        ],
    }
