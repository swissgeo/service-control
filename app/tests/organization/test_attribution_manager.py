from unittest.mock import patch

from organization.models import Attribution, Organization


@patch("organization.models.Client")
def test_external_ids(client, db):
    organization = Organization(
        sgid="org_a",
        organization_id="a",
        name_de="name_de",
        name_fr="name_fr",
        name_en="name_en",
        abbreviation_de="abbreviation_de",
        abbreviation_fr="abbreviation_fr",
        abbreviation_en="abbreviation_en",
    )
    organization.save()

    Attribution(
        attribution_id="a",
        data_source=Attribution.DataSource.BOD_CONTACT_ORGANIZATION,
        external_ids=[
            {"source": Attribution.DataSource.BOD_CONTACT_ORGANIZATION, "id": "1"},
            {"source": Attribution.DataSource.BOD_CONTACT_ORGANIZATION, "id": "2"},
        ],
        organization=organization,
    ).save()
    Attribution(
        attribution_id="b",
        data_source=Attribution.DataSource.BOD_CONTACT_ORGANIZATION,
        external_ids=[
            {"source": Attribution.DataSource.BOD_CONTACT_ORGANIZATION, "id": "2"},
            {"source": Attribution.DataSource.BOD_CONTACT_ORGANIZATION, "id": "3"},
        ],
        organization=organization,
    ).save()
    Attribution(
        attribution_id="c",
        data_source=Attribution.DataSource.GEODIENSTE,
        external_ids=[
            {"source": Attribution.DataSource.BOD_CONTACT_ORGANIZATION, "id": "5"},
            {"source": Attribution.DataSource.GEODIENSTE, "id": "1"},
            {"source": Attribution.DataSource.GEODIENSTE, "id": "2"},
            {"source": Attribution.DataSource.GEODIENSTE, "id": "3"},
            {"source": Attribution.DataSource.GEODIENSTE, "id": "4"},
        ],
        organization=organization,
    ).save()

    # test existing_external_ids
    assert Attribution.objects.existing_external_ids(
        Attribution.DataSource.BOD_CONTACT_ORGANIZATION
    ) == {"1", "2", "3", "5"}

    assert Attribution.objects.existing_external_ids(Attribution.DataSource.GEODIENSTE) == {
        "1",
        "2",
        "3",
        "4",
    }

    # test remove_external_id
    Attribution.objects.remove_external_id(Attribution.DataSource.GEODIENSTE, "2")

    # test existing_external_ids
    assert Attribution.objects.existing_external_ids(
        Attribution.DataSource.BOD_CONTACT_ORGANIZATION
    ) == {"1", "2", "3", "5"}

    assert Attribution.objects.existing_external_ids(Attribution.DataSource.GEODIENSTE) == {
        "1",
        "3",
        "4",
    }
