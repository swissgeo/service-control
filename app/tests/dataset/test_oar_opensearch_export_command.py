"""End-to-end tests for the `oar_opensearch_export` management command.

The command has two output modes:

  * `--dump <dir>` builds the documents and writes them to disk, one JSON file per document,
    without ever talking to OpenSearch. These tests run it against a `tmp_path` and assert on
    the files produced.
  * the default mode talks to an OpenSearch cluster, building a fresh timestamped generation and
    swapping the aliases over. There is no cluster in the test environment, so the client and the
    `helpers.bulk` call are mocked; the tests assert on the documents the command *would* have
    indexed and on the index/alias calls it makes.
"""

import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from dataservice.models import WMSDataservice
from dataset.management.commands.oar_opensearch_export import (
    TYPE_TO_INDEX,
    _is_generation_of,
    _rewrite_dist_links,
)
from dataset.models import Dataset
from distribution.models import ExternalWMSDistribution

COMMAND = "oar_opensearch_export"
MODULE = "dataset.management.commands.oar_opensearch_export"


def _make_dataservice() -> WMSDataservice:
    dataservice = WMSDataservice(
        dataservice_id="wmts-geoadminch",
        title="WMTS geo.admin.ch",
        documentation_url_de="https://docs.geo.admin.ch/visualize-data/wmts.html",
        languages=["de", "fr", "en", "it"],
        capabilities_url="https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang={lang}",
    )
    dataservice.save()
    return dataservice


def _make_dataset() -> Dataset:
    dataset = Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="Rote Liste Moose",
        title_short_fr="Liste rouge mousses",
        title_short_en="Red list bryophytes",
        title_short_it="Lista rossa biofite",
        description_de="Beschreibung",
        description_fr="Description",
        description_en="Description",
        description_it="Descrizione",
        geocat_id="07b046a7-1b21-4cd0-b605-a113f2e5e94d",
    )
    dataset.save()
    return dataset


def _make_distribution(dataset: Dataset, dataservice: WMSDataservice) -> ExternalWMSDistribution:
    distribution = ExternalWMSDistribution(
        distribution_id="ch.bafu.moose:wms",
        dataset=dataset,
        title_de="WMS Layer (DE)",
        title_fr="WMS Layer (FR)",
        title_it="WMS Layer (IT)",
        title_en="WMS Layer (EN)",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_it="Description (IT)",
        description_en="Description (EN)",
        dataservice=dataservice,
        wms_layer_name_de="ch.bafu.moose",
        opacity=1.0,
        gutter=0,
    )
    distribution.save()
    return distribution


def _read_dump(dump_dir: Path, index: str, doc_id: str) -> dict:
    return json.loads((dump_dir / index / f"{doc_id}.json").read_text())


def _mock_client() -> MagicMock:
    """A stand-in OpenSearch client for a fresh cluster.

    `exists`/`exists_alias` are False (no concrete index blocks the swap, no previous alias
    to detach) and `get` returns no generations, so the alias swap and prune run cleanly.
    """
    client = MagicMock()
    client.indices.exists.return_value = False
    client.indices.exists_alias.return_value = False
    client.indices.get.return_value = {}
    return client


OAR_BASE_URL = "https://services.example.ch/api/oar/staticv2"
OAS_BASE_URL = "https://services.example.ch/api/oas/v0"


def test_rewrite_dist_links_keeps_external_link_as_is():
    """A link with an unhandled rel and a non-OAR/OAS href falls through and is kept verbatim."""
    external = {"href": "https://not-rewritten.org", "rel": "license", "title": "License"}
    links = [
        {"href": f"{OAR_BASE_URL}/collections/x/items/y", "rel": "self"},  # dropped
        external,  # kept as-is
    ]

    result = _rewrite_dist_links(links, OAR_BASE_URL, OAS_BASE_URL, "ch.bafu.moose")

    assert result == [external]
    # The dict is passed through unchanged, not rewritten into a relative path.
    assert result[0] is external


def test_rewrite_dist_links_drops_internal_oar_link_without_mapping():
    """An OAR/OAS-internal link with no defined mapping (e.g. featureinfo) is dropped."""
    links = [
        {"href": f"{OAR_BASE_URL}/some/featureinfo", "rel": "featureinfo"},
        {"href": "https://not-rewritten.org", "rel": "license"},
    ]

    result = _rewrite_dist_links(links, OAR_BASE_URL, OAS_BASE_URL, "ch.bafu.moose")

    assert result == [{"href": "https://not-rewritten.org", "rel": "license"}]



def test_dump_writes_one_file_per_document(db, tmp_path):
    dataservice = _make_dataservice()
    dataset = _make_dataset()
    _make_distribution(dataset, dataservice)

    out = StringIO()
    call_command(COMMAND, dump=str(tmp_path), verbosity=2, stdout=out)

    # One file per document, in the per-index sub-directories.
    assert (tmp_path / "geoadmin-services" / "wmts-geoadminch.json").is_file()
    assert (tmp_path / "swissgeo-catalog" / "ch.bafu.moose.json").is_file()
    assert (tmp_path / "swissgeo-distributions" / "ch.bafu.moose.json").is_file()


def test_dump_service_document(db, tmp_path):
    _make_dataservice()

    call_command(COMMAND, dump=str(tmp_path), verbosity=0)

    doc = _read_dump(tmp_path, "geoadmin-services", "wmts-geoadminch")
    assert doc["id"] == "wmts-geoadminch"
    assert doc["type"] == "Feature"
    assert doc["properties"] == {
        "type": "ogc:wms",
        "title": {
            "de": "WMTS geo.admin.ch",
            "fr": "WMTS geo.admin.ch",
            "it": "WMTS geo.admin.ch",
            "en": "WMTS geo.admin.ch",
        },
    }
    # The per-language 'alternate' self links are dropped; the (de) self/collection and the
    # external links are kept.
    rels = [link["rel"] for link in doc["links"]]
    assert "alternate" not in rels
    assert rels == ["self", "collection", "service-doc", "about"]
    assert doc["linkTemplates"] == []


def test_dump_dataset_document(db, tmp_path):
    _make_dataset()

    call_command(COMMAND, dump=str(tmp_path), verbosity=0)

    doc = _read_dump(tmp_path, "swissgeo-catalog", "ch.bafu.moose")
    assert doc["$schema"].endswith("recordGeoJSON.yaml")
    assert doc["id"] == "ch.bafu.moose"
    assert doc["type"] == "Feature"
    assert doc["geometry"]["type"] == "Polygon"

    # Only external links survive, plus the (relative) distributions link.
    assert doc["links"] == [
        {
            "href": "https://www.geocat.ch/geonetwork/srv/ger/catalog.search#/metadata/07b046a7-1b21-4cd0-b605-a113f2e5e94d",
            "rel": "alternate",
            "title": "GeoCat Metadata",
            "type": "text/html",
        },
        {
            "href": "/collections/swissgeo-distributions/items/ch.bafu.moose",
            "rel": "distributions",
            "title": "Distributions",
        },
    ]

    # 'title'/'description' become multilingual objects; the singular 'language' is dropped.
    assert "language" not in doc["properties"]
    assert doc["properties"]["type"] == "Dataset"
    assert doc["properties"]["title"] == {
        "de": "Rote Liste Moose",
        "fr": "Liste rouge mousses",
        "it": "Lista rossa biofite",
        "en": "Red list bryophytes",
    }
    assert doc["properties"]["description"] == {
        "de": "Beschreibung",
        "fr": "Description",
        "it": "Descrizione",
        "en": "Description",
    }


def test_dump_distribution_document(db, tmp_path):
    dataservice = _make_dataservice()
    dataset = _make_dataset()
    _make_distribution(dataset, dataservice)

    call_command(COMMAND, dump=str(tmp_path), verbosity=0)

    doc = _read_dump(tmp_path, "swissgeo-distributions", "ch.bafu.moose")
    assert doc["id"] == "ch.bafu.moose"
    assert doc["type"] == "FeatureCollection"
    assert doc["properties"]["title"] == {
        "de": "Rote Liste Moose",
        "fr": "Liste rouge mousses",
        "it": "Lista rossa biofite",
        "en": "Red list bryophytes",
    }

    assert len(doc["features"]) == 1
    feature = doc["features"][0]
    assert feature["id"] == "ch.bafu.moose:wms"
    assert feature["type"] == "Feature"
    # dataset/dataservice links rewritten to relative index paths; styledby kept (language
    # stripped); the internal self/collection/featureinfo links are dropped.
    assert feature["links"] == [
        {
            "href": "/collections/swissgeo-catalog/items/ch.bafu.moose",
            "rel": "dataset",
            "title": "Dataset Record",
        },
        {
            "href": "/collections/geoadmin-services/items/wmts-geoadminch",
            "rel": "dataservice",
        },
        {
            "href": "https://services.swissgeo.ch/api/oas/v0/styles/ch.bafu.moose:wms:style",
            "rel": "styledby",
            "title": "Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
            "type": "application/json",
        },
    ]
    # Translated fields are {lang: value} objects, like datasets/services.
    assert feature["properties"]["type"] == "Distribution"
    assert feature["properties"]["protocol"] == "ogc:wms"
    assert feature["properties"]["externalIds"] == ["ch.bafu.moose"]
    assert feature["properties"]["title"] == {
        "de": "WMS Layer (DE)",
        "fr": "WMS Layer (FR)",
        "it": "WMS Layer (IT)",
        "en": "WMS Layer (EN)",
    }
    assert feature["properties"]["description"] == {
        "de": "Description (DE)",
        "fr": "Description (FR)",
        "it": "Description (IT)",
        "en": "Description (EN)",
    }

@patch(f"{MODULE}.helpers.bulk", return_value=(0, []))
@patch(f"{MODULE}.Command.get_client")
def test_export_creates_generation_indices_and_bulk_indexes(get_client, bulk, db):
    dataservice = _make_dataservice()
    dataset = _make_dataset()
    _make_distribution(dataset, dataservice)
    client = _mock_client()
    get_client.return_value = client

    out = StringIO()
    call_command(COMMAND, verbosity=2, stdout=out)

    # A fresh timestamped generation is created for each of the three aliases.
    created = {call.kwargs["index"] for call in client.indices.create.call_args_list}
    assert len(created) == 3
    for alias in ("geoadmin-services", "swissgeo-catalog", "swissgeo-distributions"):
        assert any(_is_generation_of(index, alias) for index in created), alias

    # helpers.bulk is called once per record type; the documents go into the generation index,
    # keyed by the alias each generation belongs to.
    assert bulk.call_count == 3
    indexed: dict[str, list[dict]] = {}
    for call in bulk.call_args_list:
        actions = list(call.args[1])
        assert actions, "expected at least one document per index"
        target = actions[0]["_index"]
        alias = next(a for a in TYPE_TO_INDEX.values() if _is_generation_of(target, a))
        indexed[alias] = actions

    # The service document reaches the services generation with its id and source.
    service_actions = indexed["geoadmin-services"]
    assert len(service_actions) == 1
    action = service_actions[0]
    assert action["_id"] == "wmts-geoadminch"
    assert action["_source"]["id"] == "wmts-geoadminch"
    assert action["_source"]["properties"]["title"]["de"] == "WMTS geo.admin.ch"

    # The dataset and distribution documents reach their respective generations.
    assert [a["_id"] for a in indexed["swissgeo-catalog"]] == ["ch.bafu.moose"]
    assert [a["_id"] for a in indexed["swissgeo-distributions"]] == ["ch.bafu.moose"]


@patch(f"{MODULE}.helpers.bulk", return_value=(0, []))
@patch(f"{MODULE}.Command.get_client")
def test_export_swaps_all_aliases_in_a_single_request(get_client, bulk, db):
    _make_dataservice()
    _make_dataset()
    client = _mock_client()
    get_client.return_value = client

    call_command(COMMAND, verbosity=0)

    # The swap happens in one _aliases call; on a fresh cluster it is one 'add' per alias,
    # each pointing at the generation just built.
    client.indices.update_aliases.assert_called_once()
    actions = client.indices.update_aliases.call_args.kwargs["body"]["actions"]
    added = {a["add"]["alias"]: a["add"]["index"] for a in actions if "add" in a}
    assert set(added) == set(TYPE_TO_INDEX.values())
    for alias, index in added.items():
        assert _is_generation_of(index, alias)


@patch(f"{MODULE}.helpers.bulk")
@patch(f"{MODULE}.Command.get_client")
def test_export_aborts_before_swap_when_a_document_fails_to_index(get_client, bulk, db):
    """A bulk error raises and stops the run *before* any alias is moved.

    The half-filled generation is left behind for inspection, but the aliases keep pointing at
    the previous generation, so readers are unaffected -- the safety property the command relies
    on for atomicity.
    """
    _make_dataservice()
    client = _mock_client()
    get_client.return_value = client
    # helpers.bulk reports one failed document (raise_on_error=False, so it returns errors).
    bulk.return_value = (0, [{"index": {"error": "mapper_parsing_exception"}}])

    out = StringIO()
    with pytest.raises(CommandError, match="documents failed to index"):
        call_command(COMMAND, verbosity=2, stdout=out, stderr=out)

    # The command aborts on the first failing type and never reaches the alias swap or prune.
    client.indices.update_aliases.assert_not_called()
    client.indices.delete.assert_not_called()


@patch(f"{MODULE}.helpers.bulk", return_value=(0, []))
@patch(f"{MODULE}.Command.get_client")
def test_export_does_not_dump_to_disk(get_client, bulk, db, tmp_path):
    """A real (non-dump) export never writes files."""
    _make_dataservice()
    get_client.return_value = _mock_client()

    call_command(COMMAND, verbosity=0)

    assert not any(tmp_path.iterdir())
    assert bulk.called
