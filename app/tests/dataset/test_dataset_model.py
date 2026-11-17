from django.core.exceptions import ValidationError
from django.db import IntegrityError

import pytest

from dataset.models import Dataset, DatasetToDataset, DatasetToUnit
from organization.models import Unit
from thesaurus.models import Concept, Thesaurus


@pytest.fixture(name="dataset")
def fixture_dataset(db):
    return Dataset.objects.create(
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


def test_dataset_all_required_fields(dataset):
    dataset.full_clean()


@pytest.mark.parametrize(
    "field",
    [
        "dataset_id",
        "title_de",
        "title_fr",
        "title_en",
        "description_de",
        "description_fr",
        "description_en",
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
        "title_de",
        "title_fr",
        "title_en",
        "description_de",
        "description_fr",
        "description_en",
    ],
)
def test_dataset_required_field_null(field, dataset):
    setattr(dataset, field, None)
    with pytest.raises(ValidationError):
        dataset.full_clean()


@pytest.mark.parametrize(
    "field",
    ["dataset_id"],
)
def test_dataset_unique_fields(field, dataset):
    new_dataset = Dataset(
        sgid="dat_xyz",
        dataset_id="xyz",
        title_de="xyz",
        title_fr="xyz",
        title_en="xyz",
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
        sgid="dat_parent",
        dataset_id="parent",
        title_de="Title (DE)",
        title_fr="Title (FR)",
        title_en="Title (EN)",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        geocat_id="parent",
    )

    child = Dataset.objects.create(
        sgid="dat_child",
        dataset_id="child",
        title_de="Title (DE)",
        title_fr="Title (FR)",
        title_en="Title (EN)",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        geocat_id="child",
    )

    relation = DatasetToDataset(subject=child, role=DatasetToDataset.Role.CHILD, object=parent)
    relation.save()

    assert str(relation) == "child is a child of parent"

    assert parent.related_datasets(DatasetToDataset.Role.CHILD).first() == child
    assert parent.related_datasets(DatasetToDataset.Role.CHILD, reverse=True).first() is None

    assert child.related_datasets(DatasetToDataset.Role.CHILD).first() is None
    assert child.related_datasets(DatasetToDataset.Role.CHILD, reverse=True).first() == parent


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


def test_dataset_concepts(dataset):
    thesaurus = Thesaurus.objects.create(thesaurus_id="thesaurus")
    concept = Concept.objects.create(concept_id="http://example/concept#1", thesaurus=thesaurus)
    dataset.concepts.set([concept])

    dataset.delete()
    assert Dataset.objects.count() == 0
    assert Thesaurus.objects.count() > 0
    assert Concept.objects.count() > 0


def test_add_external_id(dataset):
    dataset.add_external_id(Dataset.DataSource.GEODIENSTE, "b")
    dataset.add_external_id(Dataset.DataSource.BOD_DATASET, "a")
    dataset.add_external_id(Dataset.DataSource.BOD_DATASET, "a")

    assert dataset.external_ids == [
        {"source": Dataset.DataSource.BOD_DATASET, "id": "a"},
        {"source": Dataset.DataSource.GEODIENSTE, "id": "b"},
    ]


@pytest.mark.parametrize(
    ("sgid", "valid"),
    [
        ("dat_a", True),
        ("dat_neophyten-portulak-heusenkraut", True),
        ("dat_2024-census", True),
        ("dat_", False),  # empty body
        ("dst_foo", False),  # other prefix
        ("dat_Foo", False),  # uppercase
        ("dat_foo_bar", False),  # underscore in body
        ("dat_foo--bar", False),  # double hyphen
        ("dat_foo-", False),  # trailing hyphen
        ("dat_foo\n", False),  # trailing newline
        ("ch.bafu.neophyten-portulak_heusenkraut", False),  # raw BGDI layer name
    ],
)
def test_dataset_sgid_constraint(db, sgid, valid):
    if valid:
        Dataset(sgid=sgid).save()
        assert Dataset.objects.filter(sgid=sgid).exists()
    else:
        with pytest.raises(IntegrityError):
            Dataset(sgid=sgid).save()
