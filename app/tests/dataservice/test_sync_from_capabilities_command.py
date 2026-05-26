from unittest.mock import MagicMock, patch

from pystac import Collection
from six import StringIO

from django.core.management import call_command

import pytest

from dataset.models import Dataset
from distribution.models import Distribution, ExternalGeoJSONDistribution, ExternalStacDistribution


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

    with patch("dataservice.management.commands.sync_from_capabilities.Client") as client_cls:
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

    out = StringIO()
    call_command("sync_from_capabilities", stac=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert (
        "Added distribution for collection_id ch.bafu.moose to dataset ORPHANAGE from "
        "dataservice stac-api-landingpage." in out
    )

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

    out = StringIO()
    call_command("sync_from_capabilities", stac=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert (
        "Added distribution for collection_id ch.bafu.moose to dataset ch.bafu.moose from "
        "dataservice stac-api-landingpage." in out
    )

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

    out = StringIO()
    call_command("sync_from_capabilities", stac=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert (
        "Added distribution for collection_id ch.bafu.moose to dataset ORPHANAGE from "
        "dataservice stac-api-landingpage." in out
    )

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

    out = StringIO()
    call_command("sync_from_capabilities", stac=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert (
        "Updated distribution for collection_id ch.bafu.moose to dataset "
        "ch.bafu.moose from dataservice stac-api-landingpage." in out
    )

    dist = ExternalStacDistribution.objects.first()
    assert dist
    assert dist.dataset.dataset_id == "ch.bafu.moose"


def test_command_cleans_obsolete_stac_distributions(stac, db):
    out = StringIO()
    call_command("loaddata", "app/fixtures/dataservice.json", stdout=out)
    out = out.getvalue()
    assert "Installed" in out

    dataset = Dataset(
        dataset_id="ch.bazl.luftfahrthindernis",
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
    ExternalGeoJSONDistribution(
        distribution_id="ch.bazl.luftfahrthindernis:geojson", dataset=dataset
    ).save()
    ExternalStacDistribution(
        distribution_id="ch.bazl.luftfahrthindernis:stac",
        dataset=dataset,
        data_source=Distribution.DATA_SOURCE_CHOICE_SERVICE_CAPABILITIES,
    ).save()

    stac.return_value = [Collection(id="ch.bafu.moose", description="", extent="")]

    # Only report
    out = StringIO()
    call_command("sync_from_capabilities", stac=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Obsolete distribution found: ch.bazl.luftfahrthindernis:stac" in out
    assert Distribution.objects.count() == 3

    # Clean
    out = StringIO()
    call_command("sync_from_capabilities", stac=True, clean=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removing obsolete distribution ch.bazl.luftfahrthindernis:stac" in out

    assert {d.distribution_id for d in Distribution.objects.all()} == {
        "ch.bazl.luftfahrthindernis:geojson",
        "ch.bafu.moose:stac",
    }
