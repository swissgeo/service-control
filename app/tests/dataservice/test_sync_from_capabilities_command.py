from unittest.mock import MagicMock, patch

from pystac import Collection
from six import StringIO

from django.core.management import call_command

import pytest

from dataset.models import Dataset
from distribution.models import Distribution, ExternalStacDistribution


@pytest.fixture(name="stac")
def fixture_stac():
    """Mocks the pystac client.

    Returns the collections search endpoint.

    Use it like this:

        from pystac import Collection

        def test_foo(stac):
            stac.return_value = [
                Collection(...),
            ]

    """

    with patch("dataservice.models.Client") as client_cls:
        collections = MagicMock(name="collections")
        client = MagicMock(name="client")
        client.collection_search.return_value.collections = collections
        client_cls.open.return_value = client
        yield collections


def test_command_creates_default_orphaned_dataset(db):
    out = StringIO()
    call_command("sync_from_capabilities", verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Added orphanage dataset 'ORPHANAGE'" in out
    assert Dataset.objects.filter(dataset_id="ORPHANAGE").first()


def test_command_creates_orphaned_dataset(db):
    out = StringIO()
    call_command("sync_from_capabilities", orphanage_dataset="ods", verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Added orphanage dataset 'ods'" in out
    assert Dataset.objects.filter(dataset_id="ods").first()


def test_command_creates_stac_distributions_in_orphaned(stac, db):
    out = StringIO()
    call_command("loaddata", "app/fixtures/dataservice.json", stdout=out)
    out = out.getvalue()
    assert "Installed" in out

    stac.return_value = [Collection(id="ch.bafu.moose", description="", extent="")]

    call_command("sync_from_capabilities", stac=True)

    dataset = Dataset.objects.filter(dataset_id="ORPHANAGE").first()
    assert dataset

    dist = dataset.distribution_set.first()
    assert dist
    assert dist.protocol == "ogcapi:stac"
    assert dist.distribution_id == "ch.bafu.moose:stac"
    assert dist.stac_collection_id == "ch.bafu.moose"
    assert dist.data_source == Distribution.DATA_SOURCE_CHOICE_SERVICE_CAPABILITIES
    assert dist.title == "STAC Download Collection"


def test_command_creates_stac_distributions(stac, db):
    dataset = Dataset(
        dataset_id="ch.bafu.moose",
        geocat_id="abcd",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
    )
    dataset.save()

    out = StringIO()
    call_command("loaddata", "app/fixtures/dataservice.json", stdout=out)
    out = out.getvalue()
    assert "Installed" in out

    stac.return_value = [Collection(id="ch.bafu.moose", description="", extent="")]

    call_command("sync_from_capabilities", stac=True)

    dist = dataset.distribution_set.first()
    assert dist
    assert dist.protocol == "ogcapi:stac"
    assert dist.distribution_id == "ch.bafu.moose:stac"
    assert dist.stac_collection_id == "ch.bafu.moose"
    assert dist.data_source == Distribution.DATA_SOURCE_CHOICE_SERVICE_CAPABILITIES
    assert dist.title == "STAC Download Collection"


def test_command_updates_distribution_dataset(stac, db):
    out = StringIO()
    call_command("loaddata", "app/fixtures/dataservice.json", stdout=out)
    out = out.getvalue()
    assert "Installed" in out

    # Import to orphanage
    stac.return_value = [Collection(id="ch.bafu.moose", description="", extent="")]

    call_command("sync_from_capabilities", stac=True)

    dist = ExternalStacDistribution.objects.first()
    assert dist
    assert dist.dataset.dataset_id == "ORPHANAGE"

    # Change to existing dataset
    Dataset(
        dataset_id="ch.bafu.moose",
        geocat_id="abcd",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
    ).save()

    call_command("sync_from_capabilities", stac=True)

    dist = ExternalStacDistribution.objects.first()
    assert dist
    assert dist.dataset.dataset_id == "ch.bafu.moose"
