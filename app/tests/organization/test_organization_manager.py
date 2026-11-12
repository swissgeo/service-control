from unittest.mock import patch

from organization.models import Organization


@patch("organization.models.Client")
def test_external_ids(client, db):
    attributes = {
        "name_de": "name_de",
        "name_fr": "name_fr",
        "name_en": "name_en",
        "abbreviation_de": "abbreviation_de",
        "abbreviation_fr": "abbreviation_fr",
        "abbreviation_en": "abbreviation_en",
    }
    Organization(
        sgid="org_a",
        organization_id="a",
        data_source=Organization.DataSource.BOD_CONTACT_ORGANIZATION,
        external_ids=[
            {"source": Organization.DataSource.BOD_CONTACT_ORGANIZATION, "id": "1"},
            {"source": Organization.DataSource.BOD_CONTACT_ORGANIZATION, "id": "2"},
        ],
        **attributes,
    ).save()
    Organization(
        sgid="org_b",
        organization_id="b",
        data_source=Organization.DataSource.BOD_CONTACT_ORGANIZATION,
        external_ids=[
            {"source": Organization.DataSource.BOD_CONTACT_ORGANIZATION, "id": "2"},
            {"source": Organization.DataSource.BOD_CONTACT_ORGANIZATION, "id": "3"},
        ],
        **attributes,
    ).save()
    Organization(
        sgid="org_c",
        organization_id="c",
        data_source=Organization.DataSource.GEODIENSTE,
        external_ids=[
            {"source": Organization.DataSource.BOD_CONTACT_ORGANIZATION, "id": "5"},
            {"source": Organization.DataSource.GEODIENSTE, "id": "1"},
            {"source": Organization.DataSource.GEODIENSTE, "id": "2"},
            {"source": Organization.DataSource.GEODIENSTE, "id": "3"},
            {"source": Organization.DataSource.GEODIENSTE, "id": "4"},
        ],
        **attributes,
    ).save()

    # test existing_external_ids
    assert Organization.objects.existing_external_ids(
        Organization.DataSource.BOD_CONTACT_ORGANIZATION
    ) == {"1", "2", "3", "5"}

    assert Organization.objects.existing_external_ids(Organization.DataSource.GEODIENSTE) == {
        "1",
        "2",
        "3",
        "4",
    }

    # test remove_external_id
    Organization.objects.remove_external_id(Organization.DataSource.GEODIENSTE, "2")

    # test existing_external_ids
    assert Organization.objects.existing_external_ids(
        Organization.DataSource.BOD_CONTACT_ORGANIZATION
    ) == {"1", "2", "3", "5"}

    assert Organization.objects.existing_external_ids(Organization.DataSource.GEODIENSTE) == {
        "1",
        "3",
        "4",
    }
