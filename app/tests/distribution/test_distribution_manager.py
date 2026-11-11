from dataset.models import Dataset
from distribution.models import Distribution


def test_external_ids(db):
    dataset = Dataset.objects.create(
        sgid="dat_dataset",
        dataset_id="dataset.id",
        title_de="Title (DE)",
        title_fr="Title (FR)",
        title_en="Title (EN)",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        geocat_id="abcd",
    )
    dataset.save()

    Distribution(
        sgid="dst_a",
        distribution_id="a",
        data_source=Distribution.DataSource.BOD_LAYERS_JS,
        external_ids=[
            {"source": Distribution.DataSource.BOD_LAYERS_JS, "id": "1"},
            {"source": Distribution.DataSource.BOD_LAYERS_JS, "id": "2"},
        ],
        dataset=dataset,
    ).save()
    Distribution(
        sgid="dst_b",
        distribution_id="b",
        data_source=Distribution.DataSource.BOD_LAYERS_JS,
        external_ids=[
            {"source": Distribution.DataSource.BOD_LAYERS_JS, "id": "2"},
            {"source": Distribution.DataSource.BOD_LAYERS_JS, "id": "3"},
        ],
        dataset=dataset,
    ).save()
    Distribution(
        sgid="dst_c",
        distribution_id="c",
        data_source=Distribution.DataSource.GEODIENSTE,
        external_ids=[
            {"source": Distribution.DataSource.BOD_LAYERS_JS, "id": "5"},
            {"source": Distribution.DataSource.GEODIENSTE, "id": "1"},
            {"source": Distribution.DataSource.GEODIENSTE, "id": "2"},
            {"source": Distribution.DataSource.GEODIENSTE, "id": "3"},
            {"source": Distribution.DataSource.GEODIENSTE, "id": "4"},
        ],
        dataset=dataset,
    ).save()

    # test existing_external_ids
    assert Distribution.objects.existing_external_ids(Distribution.DataSource.BOD_LAYERS_JS) == {
        "1",
        "2",
        "3",
        "5",
    }

    assert Distribution.objects.existing_external_ids(Distribution.DataSource.GEODIENSTE) == {
        "1",
        "2",
        "3",
        "4",
    }

    # test remove_external_id
    Distribution.objects.remove_external_id(Distribution.DataSource.GEODIENSTE, "2")

    # test existing_external_ids
    assert Distribution.objects.existing_external_ids(Distribution.DataSource.BOD_LAYERS_JS) == {
        "1",
        "2",
        "3",
        "5",
    }

    assert Distribution.objects.existing_external_ids(Distribution.DataSource.GEODIENSTE) == {
        "1",
        "3",
        "4",
    }
