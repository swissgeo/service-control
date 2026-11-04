from django.db import IntegrityError

import pytest

from dataset.models import Dataset
from distribution.models import Distribution


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


@pytest.mark.parametrize(
    ("sgid", "valid"),
    [
        ("dst_a", True),
        ("dst_neophyten-portulak-heusenkraut-12345", True),
        ("dst_2024-census", True),
        ("dst_", False),  # empty body
        ("dat_foo", False),  # other prefix
        ("dst_Foo", False),  # uppercase
        ("dst_foo_bar", False),  # underscore in body
        ("dst_foo--bar", False),  # double hyphen
        ("dst_foo-", False),  # trailing hyphen
        ("dst_foo\n", False),  # trailing newline
        ("ch.bafu.neophyten-portulak_heusenkraut:wms", False),  # raw BGDI
    ],
)
def test_distribution_sgid_constraint(dataset, sgid, valid):
    if valid:
        Distribution(dataset=dataset, sgid=sgid).save()
        assert Distribution.objects.filter(sgid=sgid).exists()
    else:
        with pytest.raises(IntegrityError):
            Distribution(dataset=dataset, sgid=sgid).save()
