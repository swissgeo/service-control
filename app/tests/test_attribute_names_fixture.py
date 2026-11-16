from io import StringIO

from django.core.management import call_command
from django.db import models

import pytest

from dataservice.models import Dataservice
from dataset.models import Dataset
from distribution.models import Distribution
from organization.models import Attribution, Organization

# Fields that cannot (or should not) be set to their own name.
NOT_SELF_NAMED = {
    "id",
    "sgid",
    "polymorphic_ctype",
    "dataservice_ptr",
    "distribution_ptr",
    "data_source",
    "status",
    "created",
    "updated",
    "created_at",
    "updated_at",
    "geopolitical_entity",
    "vp_org_admin_policy_id",
    "preferred_distribution",
    "attribution",
    "organization",
    "dataset",
    "dataservice",
    "legacy_contacts",
    "meta_information",
    "opacity",
    "gutter",
    "queryable",
    "renderable",
    "languages",
    "default_language",
    "variable_epsg_list",
    "style_url",
}

# Localized texts contain descriptive content in the respective language instead of the name.
LOCALIZED_TEXT = (
    "title",
    "title_short",
    "description",
    "name",
    "abbreviation",
    "additional_search_text",
)
LANGUAGES = ("de", "fr", "en", "it", "rm")


@pytest.fixture(name="stac_dataservice")
def fixture_stac_dataservice(db):
    call_command("loaddata", "app/fixtures/dataservice.json", stdout=StringIO())


def _assert_self_named(obj: models.Model) -> None:
    for field in obj._meta.concrete_fields:  # noqa: SLF001
        name = field.name
        if name in NOT_SELF_NAMED:
            continue
        value = getattr(obj, name)
        base, _, lang = name.rpartition("_")
        if base in LOCALIZED_TEXT and lang in LANGUAGES:
            assert value, f"{type(obj).__name__}.{name}"
            assert name not in str(value), f"{type(obj).__name__}.{name}"
        elif isinstance(value, list):
            assert value == [name], f"{type(obj).__name__}.{name}"
        elif isinstance(field, models.URLField):
            assert value == f"https://example.com/{name}", f"{type(obj).__name__}.{name}"
        elif field.unique:
            assert value.split(".")[0] == name, f"{type(obj).__name__}.{name}"
        else:
            assert value == name, f"{type(obj).__name__}.{name}"


def _load() -> None:
    call_command("loaddata", "app/fixtures/attribute_names.json", stdout=StringIO())


def test_fixture_loads(stac_dataservice):
    _load()

    organization = Organization.objects.get(sgid="org_sgid")
    attribution = Attribution.objects.get(attribution_id="attribution_id")
    dataset = Dataset.objects.get(sgid="dat_sgid")
    dataservices = Dataservice.objects.filter(sgid__startswith="srv_sgid-")
    distributions = Distribution.objects.filter(dataset=dataset)

    assert attribution.organization == organization
    assert dataset.attribution == attribution
    assert dataset.preferred_distribution.sgid == "dst_sgid-wms"
    assert dataservices.count() == 5
    assert distributions.count() == 5

    for obj in [organization, attribution, dataset, *dataservices, *distributions]:
        _assert_self_named(obj)


def test_fixture_is_idempotent(stac_dataservice):
    organization_count = Organization.objects.count()
    distribution_count = Distribution.objects.count()

    _load()
    dataset_pk = Dataset.objects.get(sgid="dat_sgid").pk
    _load()

    assert Organization.objects.count() == organization_count + 1
    assert Distribution.objects.count() == distribution_count + 5
    assert Dataset.objects.get(sgid="dat_sgid").pk == dataset_pk


def test_fixture_can_be_exported(stac_dataservice, tmp_path):
    _load()

    call_command("oar_opensearch_export", dump=str(tmp_path), verbosity=0)

    assert (tmp_path / "swissgeo-catalog" / "dat_sgid.json").is_file()
    assert (tmp_path / "geoadmin-services" / "srv_sgid-wms.json").is_file()
    assert (tmp_path / "swissgeo-distributions" / "dst_sgid-geojson.json").is_file()
