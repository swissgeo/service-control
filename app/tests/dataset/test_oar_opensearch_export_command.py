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
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from dataservice.models import WMSDataservice
from dataset.management.commands.oar_opensearch_export import (
    OAR_BASE_URL,
    OAS_BASE_URL,
    _is_generation_of,
    _rewrite_dist_links,
)
from dataset.models import Dataset
from distribution.models import ExternalWMSDistribution

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


def _make_distribution(
    dataset: Dataset,
    dataservice: WMSDataservice,
    distribution_id: str = "ch.bafu.moose:wms",
    # The layer name is unique per dataservice, so a second distribution needs its own.
    wms_layer_name: str = "ch.bafu.moose",
) -> ExternalWMSDistribution:
    distribution = ExternalWMSDistribution(
        distribution_id=distribution_id,
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
        wms_layer_name_de=wms_layer_name,
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


def _mock_client_with_generations(existing: dict[str, list[str]]) -> MagicMock:
    """A stand-in client for a cluster that already holds generations of each alias.

    `existing` maps an alias to the generation indices already in the cluster, oldest first. The
    newest of them is the one the alias currently points at, as it would be after a previous run.
    """
    client = MagicMock()
    client.indices.exists.side_effect = lambda index: index in existing
    client.indices.exists_alias.side_effect = lambda name: name in existing
    client.indices.get_alias.side_effect = lambda name: {existing[name][-1]: {}}

    # Generations created during the run, so the wildcard lookup below sees them the way a real
    # cluster would -- the index just built is in the cluster by the time the prune looks.
    created: set[str] = set()
    client.indices.create.side_effect = lambda index, body: created.add(index)

    # The command discovers prune candidates with a `<alias>-*` wildcard rather than from the
    # alias, so resolve the pattern against every generation the cluster holds.
    def get(index: str, ignore_unavailable: bool) -> dict:
        alias = index.removesuffix("-*")
        return {i: {} for i in [*existing[alias], *created] if i.startswith(f"{alias}-")}

    client.indices.get.side_effect = get
    return client


# Stand-in base URLs for the `_rewrite_dist_links` unit tests below, so they don't depend on the
# environment the command happens to build its documents with.
EXAMPLE_OAR_BASE_URL = "https://services.example.ch/api/oar/staticv2"
EXAMPLE_OAS_BASE_URL = "https://services.example.ch/api/oas/v0"


def test_rewrite_dist_links_keeps_external_link_as_is():
    """A link with an unhandled rel and a non-OAR/OAS href falls through and is kept verbatim."""
    links = [
        {"href": f"{EXAMPLE_OAR_BASE_URL}/collections/x/items/y", "rel": "self"},  # dropped
        {"href": "https://not-rewritten.org", "rel": "license", "title": "License"},  # kept as-is
    ]

    result = _rewrite_dist_links(links, EXAMPLE_OAR_BASE_URL, EXAMPLE_OAS_BASE_URL, "ch.bafu.moose")

    assert result == [{"href": "https://not-rewritten.org", "rel": "license", "title": "License"}]


@pytest.mark.parametrize("rel", ["self", "collection", "alternate"])
def test_rewrite_dist_links_drops_intra_service_links(rel):
    """`self`/`collection`/`alternate` are dropped on their rel alone, whatever the href is.

    The href here is deliberately external, so an intra-service link that got rewritten to some
    other host is still dropped rather than falling through to the 'keep external links' branch.
    """
    links = [
        {"href": "https://elsewhere.example.org/collections/x/items/y", "rel": rel},
        {"href": "https://not-rewritten.org", "rel": "license"},
    ]

    result = _rewrite_dist_links(links, EXAMPLE_OAR_BASE_URL, EXAMPLE_OAS_BASE_URL, "ch.bafu.moose")

    assert result == [{"href": "https://not-rewritten.org", "rel": "license"}]


def test_rewrite_dist_links_drops_internal_oar_link_without_mapping():
    """An OAR/OAS-internal link with no defined mapping is dropped."""
    links = [
        {"href": f"{EXAMPLE_OAR_BASE_URL}/some/thing", "rel": "unmapped"},
        {"href": f"{EXAMPLE_OAS_BASE_URL}/some/other", "rel": "unmapped"},
        {"href": "https://not-rewritten.org", "rel": "license"},
    ]

    result = _rewrite_dist_links(links, EXAMPLE_OAR_BASE_URL, EXAMPLE_OAS_BASE_URL, "ch.bafu.moose")

    assert result == [{"href": "https://not-rewritten.org", "rel": "license"}]


def test_rewrite_dist_links_rewrites_featureinfo_to_the_distributions_index():
    """`featureinfo` keeps only the distribution id -- all distributions share one index.

    The OAR href names the dataset's own `<dataset_id>.distributions` collection, which has no
    OpenSearch counterpart, and the target distribution may belong to another dataset than the
    one the link is rewritten for.
    """
    links = [
        {
            "href": (
                f"{EXAMPLE_OAR_BASE_URL}/collections/ch.bafu.moose.distributions"
                "/items/ch.bafu.moose:features?language=de"
            ),
            "rel": "featureinfo",
            "hreflang": "de",
        }
    ]

    result = _rewrite_dist_links(links, EXAMPLE_OAR_BASE_URL, EXAMPLE_OAS_BASE_URL, "ch.bafu.moose")

    assert result == [
        {
            "href": "/collections/swissgeo-distributions/items/ch.bafu.moose:features",
            "rel": "featureinfo",
        }
    ]


def test_dump_writes_one_file_per_document(db, tmp_path):
    dataservice = _make_dataservice()
    dataset = _make_dataset()
    _make_distribution(dataset, dataservice)
    _make_distribution(
        dataset,
        dataservice,
        distribution_id="ch.bafu.moose:wmts",
        wms_layer_name="ch.bafu.moose.wmts",
    )

    call_command("oar_opensearch_export", dump=str(tmp_path), verbosity=0)

    # One file per document, in the per-index sub-directories.
    assert (tmp_path / "geoadmin-services" / "wmts-geoadminch.json").is_file()
    assert (tmp_path / "swissgeo-catalog" / "ch.bafu.moose.json").is_file()
    # Every distribution of the dataset gets a document of its own.
    assert sorted(p.name for p in (tmp_path / "swissgeo-distributions").iterdir()) == [
        "ch.bafu.moose:wms.json",
        "ch.bafu.moose:wmts.json",
    ]


def test_dump_service_document(db, tmp_path):
    _make_dataservice()

    call_command("oar_opensearch_export", dump=str(tmp_path), verbosity=0)

    # The per-language 'alternate' self links are dropped; the (de) self/collection and the
    # external links are kept. 'title' becomes a {lang: value} object.
    assert _read_dump(tmp_path, "geoadmin-services", "wmts-geoadminch") == {
        "id": "wmts-geoadminch",
        "type": "Feature",
        "links": [
            {
                "href": (
                    f"{OAR_BASE_URL}/collections/geoadmin.services"
                    "/items/wmts-geoadminch?language=de"
                ),
                "rel": "self",
                "title": "This Record",
                "type": "application/json",
                "hreflang": "de",
            },
            {
                "href": f"{OAR_BASE_URL}/collections/geoadmin.services?language=de",
                "rel": "collection",
                "title": "Link to the collection this item belongs to",
                "type": "application/json",
                "hreflang": "de",
            },
            {
                "href": "https://docs.geo.admin.ch/visualize-data/wmts.html",
                "rel": "service-doc",
                "title": "Service Documentation (DE)",
                "type": "application/json",
            },
            {
                "href": "https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang=de",
                "rel": "about",
                "title": "WMS Capabilities File",
                "type": "application/xml",
            },
        ],
        "properties": {
            "type": "ogc:wms",
            "title": {
                "de": "WMTS geo.admin.ch",
                "fr": "WMTS geo.admin.ch",
                "it": "WMTS geo.admin.ch",
                "en": "WMTS geo.admin.ch",
            },
        },
        "linkTemplates": [],
    }


def test_dump_dataset_document(db, tmp_path):
    _make_dataset()

    call_command("oar_opensearch_export", dump=str(tmp_path), verbosity=0)

    # Only external links survive, plus the (relative) distributions link. 'title'/'description'
    # become multilingual objects and the singular 'language' property is dropped.
    assert _read_dump(tmp_path, "swissgeo-catalog", "ch.bafu.moose") == {
        "$schema": "https://schemas.opengis.net/ogcapi/records/part1/1.0/openapi/schemas/recordGeoJSON.yaml",
        "id": "ch.bafu.moose",
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[5.96, 45.82], [5.96, 47.81], [10.49, 47.81], [10.49, 45.82], [5.96, 45.82]]
            ],
        },
        "links": [
            {
                "href": "https://www.geocat.ch/geonetwork/srv/ger/catalog.search#/metadata/07b046a7-1b21-4cd0-b605-a113f2e5e94d",
                "rel": "alternate",
                "title": "GeoCat Metadata",
                "type": "text/html",
            },
            {
                "href": "/collections/swissgeo-distributions/items?dataset=ch.bafu.moose",
                "rel": "distributions",
                "title": "Distributions",
            },
        ],
        "properties": {
            "contacts": [],
            "languages": [
                {"code": "de", "name": "Deutsch", "dir": "ltr", "alternate": "German"},
                {"code": "fr", "name": "Français", "dir": "ltr", "alternate": "French"},
                {"code": "it", "name": "Italiano", "dir": "ltr", "alternate": "Italian"},
                {"code": "en", "name": "English", "dir": "ltr", "alternate": "English"},
            ],
            "type": "Dataset",
            "title": {
                "de": "Rote Liste Moose",
                "fr": "Liste rouge mousses",
                "it": "Lista rossa biofite",
                "en": "Red list bryophytes",
            },
            "description": {
                "de": "Beschreibung",
                "fr": "Description",
                "it": "Descrizione",
                "en": "Description",
            },
        },
    }


def test_dump_distribution_document(db, tmp_path):
    dataservice = _make_dataservice()
    dataset = _make_dataset()
    _make_distribution(dataset, dataservice)

    call_command("oar_opensearch_export", dump=str(tmp_path), verbosity=0)

    # The dataset/dataservice/featureinfo links are rewritten to relative index paths and styledBy
    # is kept (with the language stripped); the internal self/collection links are dropped.
    # A WMS distribution is its own featureinfo target, so it links back to itself here.
    # Translated fields become {lang: value} objects, like datasets/services.
    assert _read_dump(tmp_path, "swissgeo-distributions", "ch.bafu.moose:wms") == {
        "id": "ch.bafu.moose:wms",
        "type": "Feature",
        "links": [
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
                "href": "/collections/swissgeo-distributions/items/ch.bafu.moose:wms",
                "rel": "featureinfo",
            },
            {
                "href": f"{OAS_BASE_URL}/styles/ch.bafu.moose:wms:style",
                "rel": "styledBy",
                "title": "Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
                "type": "application/json",
            },
        ],
        "linkTemplates": [],
        "properties": {
            "type": "Distribution",
            "dataset": "ch.bafu.moose",
            "title": {
                "de": "WMS Layer (DE)",
                "fr": "WMS Layer (FR)",
                "it": "WMS Layer (IT)",
                "en": "WMS Layer (EN)",
            },
            "description": {
                "de": "Description (DE)",
                "fr": "Description (FR)",
                "it": "Description (IT)",
                "en": "Description (EN)",
            },
            "protocol": "ogc:wms",
            "externalIds": ["ch.bafu.moose"],
        },
    }


@patch(f"{MODULE}.helpers.bulk", return_value=(0, []))
@patch(f"{MODULE}.Command.get_client")
def test_export_creates_generation_indices_and_bulk_indexes(get_client, bulk, db):
    dataservice = _make_dataservice()
    dataset = _make_dataset()
    _make_distribution(dataset, dataservice)
    client = _mock_client()
    get_client.return_value = client

    call_command("oar_opensearch_export", verbosity=0)

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
        alias = next(
            a
            for a in ("geoadmin-services", "swissgeo-catalog", "swissgeo-distributions")
            if _is_generation_of(target, a)
        )
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
    # Distributions are indexed individually, keyed by distribution id.
    assert [a["_id"] for a in indexed["swissgeo-distributions"]] == ["ch.bafu.moose:wms"]


@patch(f"{MODULE}.helpers.bulk", return_value=(0, []))
@patch(f"{MODULE}.Command.get_client")
def test_export_swaps_all_aliases_in_a_single_request(get_client, bulk, db):
    _make_dataservice()
    _make_dataset()
    client = _mock_client()
    get_client.return_value = client

    call_command("oar_opensearch_export", verbosity=0)

    # The swap happens in one _aliases call; on a fresh cluster it is one 'add' per alias,
    # each pointing at the generation just built.
    client.indices.update_aliases.assert_called_once()
    actions = client.indices.update_aliases.call_args.kwargs["body"]["actions"]
    added = {a["add"]["alias"]: a["add"]["index"] for a in actions if "add" in a}
    assert sorted(added) == ["geoadmin-services", "swissgeo-catalog", "swissgeo-distributions"]
    for alias, index in added.items():
        assert _is_generation_of(index, alias)


@patch(f"{MODULE}.helpers.bulk", return_value=(0, []))
@patch(f"{MODULE}.Command.get_client")
def test_export_detaches_previous_generation_and_prunes_the_oldest(get_client, bulk, db):
    """On a cluster with a history, the swap detaches the previous generation and prunes old ones.

    Each alias already has four generations behind it. With `--keep-generations 2` the swap moves
    the alias off the newest of them, and the prune then deletes all but the two most recent --
    including the orphans earlier swaps already detached.
    """
    _make_dataservice()
    _make_dataset()
    existing = {
        alias: [f"{alias}-2026072{n}120000" for n in range(1, 5)]
        for alias in ("geoadmin-services", "swissgeo-catalog", "swissgeo-distributions")
    }
    client = _mock_client_with_generations(existing)
    get_client.return_value = client

    call_command("oar_opensearch_export", verbosity=0, keep_generations=2)

    # Still a single _aliases request, now carrying a 'remove' of the generation each alias
    # currently points at alongside the 'add' of the one just built.
    client.indices.update_aliases.assert_called_once()
    actions = client.indices.update_aliases.call_args.kwargs["body"]["actions"]
    removed = {a["remove"]["alias"]: a["remove"]["index"] for a in actions if "remove" in a}
    assert removed == {
        "geoadmin-services": "geoadmin-services-20260724120000",
        "swissgeo-catalog": "swissgeo-catalog-20260724120000",
        "swissgeo-distributions": "swissgeo-distributions-20260724120000",
    }

    # The two oldest generations of every alias are deleted; the two most recent survive for a
    # rollback, and the generation just swapped in is never a candidate.
    deleted = sorted(call.kwargs["index"] for call in client.indices.delete.call_args_list)
    assert deleted == [
        "geoadmin-services-20260721120000",
        "geoadmin-services-20260722120000",
        "swissgeo-catalog-20260721120000",
        "swissgeo-catalog-20260722120000",
        "swissgeo-distributions-20260721120000",
        "swissgeo-distributions-20260722120000",
    ]


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

    with pytest.raises(CommandError, match="documents failed to index"):
        call_command("oar_opensearch_export", verbosity=0)

    # The command aborts on the first failing type and never reaches the alias swap or prune.
    client.indices.update_aliases.assert_not_called()
    client.indices.delete.assert_not_called()


@patch(f"{MODULE}.helpers.bulk", return_value=(0, []))
@patch(f"{MODULE}.Command.get_client")
def test_export_does_not_dump_to_disk(get_client, bulk, db, tmp_path):
    """A real (non-dump) export never writes files."""
    _make_dataservice()
    get_client.return_value = _mock_client()

    call_command("oar_opensearch_export", verbosity=0)

    assert not any(tmp_path.iterdir())
    assert bulk.called
