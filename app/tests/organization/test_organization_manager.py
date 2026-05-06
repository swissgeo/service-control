from unittest.mock import patch

from organization.models import Organization


@patch("organization.models.Client")
def test_data_source_ids(client, db):
    attributes = {
        "name_de": "name_de",
        "name_fr": "name_fr",
        "name_en": "name_en",
        "acronym_de": "acronym_de",
        "acronym_fr": "acronym_fr",
        "acronym_en": "acronym_en",
    }
    Organization(
        organization_id="a",
        data_source=Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION,
        data_source_ids=["1", "2"],
        **attributes,
    ).save()
    Organization(
        organization_id="b",
        data_source=Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION,
        data_source_ids=["2", "3"],
        **attributes,
    ).save()
    Organization(
        organization_id="c",
        data_source=Organization.DATA_SOURCE_CHOICE_USER_INPUT,
        data_source_ids=["1", "2", "3", "4"],
        **attributes,
    ).save()

    # test existing_data_source_ids
    assert Organization.objects.existing_data_source_ids(
        Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION
    ) == {"1", "2", "3"}

    assert Organization.objects.existing_data_source_ids(
        Organization.DATA_SOURCE_CHOICE_USER_INPUT
    ) == {
        "1",
        "2",
        "3",
        "4",
    }

    # test remove_data_source_id
    Organization.objects.remove_data_source_id("2")

    # test existing_data_source_ids
    assert Organization.objects.existing_data_source_ids(
        Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION
    ) == {"1", "3"}

    assert Organization.objects.existing_data_source_ids(
        Organization.DATA_SOURCE_CHOICE_USER_INPUT
    ) == {
        "1",
        "3",
        "4",
    }
