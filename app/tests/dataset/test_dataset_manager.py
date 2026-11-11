from dataset.models import Dataset


# @patch("dataset.models.Client")
def test_external_ids(db):
    attributes = {
        "title_de": "title__de",
        "title_fr": "title_fr",
        "title_en": "title_en",
        "description_de": "description_de",
        "description_fr": "description_fr",
        "description_en": "description_en",
    }
    Dataset(
        sgid="dat_a",
        dataset_id="a",
        geocat_id="a",
        data_source=Dataset.DataSource.BOD_DATASET,
        external_ids=[
            {"source": Dataset.DataSource.BOD_DATASET, "id": "1"},
            {"source": Dataset.DataSource.BOD_DATASET, "id": "2"},
        ],
        **attributes,
    ).save()
    Dataset(
        sgid="dat_b",
        dataset_id="b",
        geocat_id="b",
        data_source=Dataset.DataSource.BOD_DATASET,
        external_ids=[
            {"source": Dataset.DataSource.BOD_DATASET, "id": "2"},
            {"source": Dataset.DataSource.BOD_DATASET, "id": "3"},
        ],
        **attributes,
    ).save()
    Dataset(
        sgid="dat_c",
        dataset_id="c",
        geocat_id="c",
        data_source=Dataset.DataSource.GEODIENSTE,
        external_ids=[
            {"source": Dataset.DataSource.BOD_DATASET, "id": "5"},
            {"source": Dataset.DataSource.GEODIENSTE, "id": "1"},
            {"source": Dataset.DataSource.GEODIENSTE, "id": "2"},
            {"source": Dataset.DataSource.GEODIENSTE, "id": "3"},
            {"source": Dataset.DataSource.GEODIENSTE, "id": "4"},
        ],
        **attributes,
    ).save()

    # test existing_external_ids
    assert Dataset.objects.existing_external_ids(Dataset.DataSource.BOD_DATASET) == {
        "1",
        "2",
        "3",
        "5",
    }

    assert Dataset.objects.existing_external_ids(Dataset.DataSource.GEODIENSTE) == {
        "1",
        "2",
        "3",
        "4",
    }

    # test remove_external_id
    Dataset.objects.remove_external_id(Dataset.DataSource.GEODIENSTE, "2")

    # test existing_external_ids
    assert Dataset.objects.existing_external_ids(Dataset.DataSource.BOD_DATASET) == {
        "1",
        "2",
        "3",
        "5",
    }

    assert Dataset.objects.existing_external_ids(Dataset.DataSource.GEODIENSTE) == {
        "1",
        "3",
        "4",
    }
