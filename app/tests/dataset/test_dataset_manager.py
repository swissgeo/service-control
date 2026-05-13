from dataset.models import Dataset


# @patch("dataset.models.Client")
def test_data_source_ids(db):
    attributes = {
        "title_short_de": "title_short__de",
        "title_short_fr": "title_short_fr",
        "title_short_en": "title_short_en",
        "description_de": "description_de",
        "description_fr": "description_fr",
        "description_en": "description_en",
    }
    Dataset(
        dataset_id="a",
        geocat_id="a",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
        data_source_ids=["1", "2"],
        **attributes,
    ).save()
    Dataset(
        dataset_id="b",
        geocat_id="b",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
        data_source_ids=["2", "3"],
        **attributes,
    ).save()
    Dataset(
        dataset_id="c",
        geocat_id="c",
        data_source=Dataset.DATA_SOURCE_CHOICE_USER_INPUT,
        data_source_ids=["1", "2", "3", "4"],
        **attributes,
    ).save()

    # test existing_data_source_ids
    assert Dataset.objects.existing_data_source_ids(Dataset.DATA_SOURCE_CHOICE_BOD_DATASET) == {
        "1",
        "2",
        "3",
    }

    assert Dataset.objects.existing_data_source_ids(Dataset.DATA_SOURCE_CHOICE_USER_INPUT) == {
        "1",
        "2",
        "3",
        "4",
    }

    # test remove_data_source_id
    Dataset.objects.remove_data_source_id("2")

    # test existing_data_source_ids
    assert Dataset.objects.existing_data_source_ids(Dataset.DATA_SOURCE_CHOICE_BOD_DATASET) == {
        "1",
        "3",
    }

    assert Dataset.objects.existing_data_source_ids(Dataset.DATA_SOURCE_CHOICE_USER_INPUT) == {
        "1",
        "3",
        "4",
    }
