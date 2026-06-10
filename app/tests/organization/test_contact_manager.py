from organization.models import Contact


def test_data_source_ids(organization, db):
    Contact(
        name_de="a",
        data_source=Contact.DataSource.GEOCAT,
        data_source_ids=["1", "2"],
        organization=organization,
    ).save()
    Contact(
        name_de="b",
        data_source=Contact.DataSource.GEOCAT,
        data_source_ids=["2", "3"],
        organization=organization,
    ).save()
    Contact(
        name_de="c",
        data_source=Contact.DataSource.USER_INPUT,
        data_source_ids=["1", "2", "3", "4"],
        organization=organization,
    ).save()

    # test existing_data_source_ids
    assert Contact.objects.existing_data_source_ids(Contact.DataSource.GEOCAT) == {
        "1",
        "2",
        "3",
    }

    assert Contact.objects.existing_data_source_ids(Contact.DataSource.USER_INPUT) == {
        "1",
        "2",
        "3",
        "4",
    }

    # test remove_data_source_id
    Contact.objects.remove_data_source_id("2")

    # test existing_data_source_ids
    assert Contact.objects.existing_data_source_ids(Contact.DataSource.GEOCAT) == {"1", "3"}

    assert Contact.objects.existing_data_source_ids(Contact.DataSource.USER_INPUT) == {
        "1",
        "3",
        "4",
    }
