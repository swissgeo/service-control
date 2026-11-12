from dataservice.models import Dataservice


def test_external_ids(db):
    Dataservice(
        sgid="srv_a",
        dataservice_id="a",
        data_source=Dataservice.DataSource.FIXTURE,
        external_ids=[
            {"source": Dataservice.DataSource.FIXTURE, "id": "1"},
            {"source": Dataservice.DataSource.FIXTURE, "id": "2"},
        ],
    ).save()
    Dataservice(
        sgid="srv_b",
        dataservice_id="b",
        data_source=Dataservice.DataSource.FIXTURE,
        external_ids=[
            {"source": Dataservice.DataSource.FIXTURE, "id": "2"},
            {"source": Dataservice.DataSource.FIXTURE, "id": "3"},
        ],
    ).save()
    Dataservice(
        sgid="srv_c",
        dataservice_id="c",
        data_source=Dataservice.DataSource.GEODIENSTE,
        external_ids=[
            {"source": Dataservice.DataSource.FIXTURE, "id": "5"},
            {"source": Dataservice.DataSource.GEODIENSTE, "id": "1"},
            {"source": Dataservice.DataSource.GEODIENSTE, "id": "2"},
            {"source": Dataservice.DataSource.GEODIENSTE, "id": "3"},
            {"source": Dataservice.DataSource.GEODIENSTE, "id": "4"},
        ],
    ).save()

    # test existing_external_ids
    assert Dataservice.objects.existing_external_ids(Dataservice.DataSource.FIXTURE) == {
        "1",
        "2",
        "3",
        "5",
    }

    assert Dataservice.objects.existing_external_ids(Dataservice.DataSource.GEODIENSTE) == {
        "1",
        "2",
        "3",
        "4",
    }

    # test remove_external_id
    Dataservice.objects.remove_external_id(Dataservice.DataSource.GEODIENSTE, "2")

    # test existing_external_ids
    assert Dataservice.objects.existing_external_ids(Dataservice.DataSource.FIXTURE) == {
        "1",
        "2",
        "3",
        "5",
    }

    assert Dataservice.objects.existing_external_ids(Dataservice.DataSource.GEODIENSTE) == {
        "1",
        "3",
        "4",
    }
