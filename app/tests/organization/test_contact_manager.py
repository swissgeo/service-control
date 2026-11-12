from organization.models import Contact


def test_external_ids(organization, db):
    Contact(
        name_de="a",
        data_source=Contact.DataSource.GEOCAT,
        external_ids=[
            {"source": Contact.DataSource.GEOCAT, "id": "1"},
            {"source": Contact.DataSource.GEOCAT, "id": "2"},
        ],
        organization=organization,
    ).save()
    Contact(
        name_de="b",
        data_source=Contact.DataSource.GEOCAT,
        external_ids=[
            {"source": Contact.DataSource.GEOCAT, "id": "2"},
            {"source": Contact.DataSource.GEOCAT, "id": "3"},
        ],
        organization=organization,
    ).save()
    Contact(
        name_de="c",
        data_source=Contact.DataSource.GEODIENSTE,
        external_ids=[
            {"source": Contact.DataSource.GEOCAT, "id": "5"},
            {"source": Contact.DataSource.GEODIENSTE, "id": "1"},
            {"source": Contact.DataSource.GEODIENSTE, "id": "2"},
            {"source": Contact.DataSource.GEODIENSTE, "id": "3"},
            {"source": Contact.DataSource.GEODIENSTE, "id": "4"},
        ],
        organization=organization,
    ).save()

    # test existing_external_ids
    assert Contact.objects.existing_external_ids(Contact.DataSource.GEOCAT) == {"1", "2", "3", "5"}

    assert Contact.objects.existing_external_ids(Contact.DataSource.GEODIENSTE) == {
        "1",
        "2",
        "3",
        "4",
    }

    # test remove_external_id
    Contact.objects.remove_external_id(Contact.DataSource.GEODIENSTE, "2")

    # test existing_external_ids
    assert Contact.objects.existing_external_ids(Contact.DataSource.GEOCAT) == {"1", "2", "3", "5"}

    assert Contact.objects.existing_external_ids(Contact.DataSource.GEODIENSTE) == {
        "1",
        "3",
        "4",
    }
