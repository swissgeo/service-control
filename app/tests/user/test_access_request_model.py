import pytest

from user.models import AccessRequest


def test_object_stored_as_expected_for_valid_input(organization, user_without_org):
    access_request_in = {
        "user": user_without_org,
        "organization": organization,
    }
    created = AccessRequest.objects.create(**access_request_in)
    assert created is not None
    assert created.user == access_request_in["user"]
    assert created.organization == access_request_in["organization"]
    assert created.state == AccessRequest.AccessRequestState.PENDING


def test_only_one_pending_access_request_per_user(organization, user_without_org):
    access_request_in = {
        "user": user_without_org,
        "organization": organization,
    }
    created = AccessRequest.objects.create(**access_request_in)
    assert created is not None

    with pytest.raises(Exception, match="User already has a pending access request"):
        AccessRequest.objects.create(**access_request_in)


def test_user_can_have_multiple_access_requests_with_different_states(
    organization, user_without_org
):
    access_request_in = {
        "user": user_without_org,
        "organization": organization,
    }
    created = AccessRequest.objects.create(**access_request_in)
    assert created is not None

    created.state = AccessRequest.AccessRequestState.APPROVED
    created.save()

    # Now we should be able to create another pending access request for the same user
    new_access_request = AccessRequest.objects.create(**access_request_in)
    assert new_access_request is not None
    assert new_access_request.state == AccessRequest.AccessRequestState.PENDING


def test_user_cannot_create_access_request_if_belongs_to_organization(organization, user):
    access_request_in = {
        "user": user,
        "organization": organization,
    }

    with pytest.raises(Exception, match="User already belongs to an organization"):
        AccessRequest.objects.create(**access_request_in)
