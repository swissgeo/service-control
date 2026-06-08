from django.core.exceptions import ValidationError

import pytest

from dataset.models import Dataset, DatasetToDataset, DatasetToUnit
from organization.models import Unit
from thesaurus.models import Keyword, Thesaurus


@pytest.fixture(name="dataset")
def fixture_dataset(db):
    return Dataset.objects.create(
        dataset_id="dataset.id",
        title_short_de="Title (DE)",
        title_short_fr="Title (FR)",
        title_short_en="Title (EN)",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        geocat_id="abcd",
    )


def test_dataset_all_required_fields(dataset):
    dataset.full_clean()


@pytest.mark.parametrize(
    "field",
    [
        "dataset_id",
        "title_short_de",
        "title_short_fr",
        "title_short_en",
        "description_de",
        "description_fr",
        "description_en",
        "geocat_id",
    ],
)
def test_dataset_required_field_empty(field, dataset):
    setattr(dataset, field, "")
    with pytest.raises(ValidationError):
        dataset.full_clean()


@pytest.mark.parametrize(
    "field",
    [
        "dataset_id",
        "title_short_de",
        "title_short_fr",
        "title_short_en",
        "description_de",
        "description_fr",
        "description_en",
        "geocat_id",
    ],
)
def test_dataset_required_field_null(field, dataset):
    setattr(dataset, field, None)
    with pytest.raises(ValidationError):
        dataset.full_clean()


@pytest.mark.parametrize(
    "field",
    [
        "dataset_id",
        "geocat_id",
    ],
)
def test_dataset_unique_fields(field, dataset):
    new_dataset = Dataset(
        dataset_id="xyz",
        title_short_de="xyz",
        title_short_fr="xyz",
        title_short_en="xyz",
        description_de="xyz",
        description_fr="xyz",
        description_en="xyz",
        geocat_id="xyz",
    )
    setattr(new_dataset, field, getattr(dataset, field))
    with pytest.raises(ValidationError):
        new_dataset.full_clean()


def test_dataset_to_dataset(db):
    parent = Dataset.objects.create(
        dataset_id="parent",
        title_short_de="Title (DE)",
        title_short_fr="Title (FR)",
        title_short_en="Title (EN)",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        geocat_id="parent",
    )

    child = Dataset.objects.create(
        dataset_id="child",
        title_short_de="Title (DE)",
        title_short_fr="Title (FR)",
        title_short_en="Title (EN)",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        geocat_id="child",
    )

    relation = DatasetToDataset(subject=parent, role=DatasetToDataset.Role.PARENT, object=child)
    relation.save()

    assert str(relation) == "parent is a parent of child"

    assert parent.related_datasets(DatasetToDataset.Role.PARENT).first() is None
    assert parent.related_datasets(DatasetToDataset.Role.PARENT, reverse=True).first() == child

    assert child.related_datasets(DatasetToDataset.Role.PARENT).first() == parent
    assert child.related_datasets(DatasetToDataset.Role.PARENT, reverse=True).first() is None


def test_dataset_unit(dataset, unit):
    dataset_unit = DatasetToUnit.objects.create(
        dataset=dataset, unit=unit, role=DatasetToUnit.Role.OWNER
    )

    assert unit.dataset_units.first() == dataset_unit

    dataset.delete()
    assert DatasetToUnit.objects.count() == 0
    assert Unit.objects.count() > 0


def test_dataset_contact(dataset, unit):
    dataset_unit = DatasetToUnit.objects.create(
        dataset=dataset, unit=unit, role=DatasetToUnit.Role.OWNER
    )
    assert unit.dataset_units.first() == dataset_unit

    dataset.delete()
    assert Dataset.objects.count() == 0
    assert DatasetToUnit.objects.count() == 0
    assert Unit.objects.count() > 0


def test_dataset_keywords(dataset):
    thesaurus = Thesaurus.objects.create(thesaurus_id="thesaurus")
    keyword = Keyword.objects.create(keyword_id="http://example/concept#1", thesaurus=thesaurus)
    dataset.keywords.set([keyword])

    dataset.delete()
    assert Dataset.objects.count() == 0
    assert Thesaurus.objects.count() > 0
    assert Keyword.objects.count() > 0


def test_add_data_source_id(dataset):
    dataset.add_data_source_id("b")
    dataset.add_data_source_id("a")
    dataset.add_data_source_id("a")

    assert dataset.data_source_ids == ["a", "b"]
