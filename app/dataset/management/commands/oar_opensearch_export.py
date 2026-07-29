"""Export data entities into the OpenSearch indices backing the OGC API Records search.

This command exports the entities from DataService, Dataset and Distribution models from Django
to an OpenSearch database in OGC API Records format.

The OGC API Records are mainly consumed by the SWISSGEO frontend to search for datasets.

This command potentially could be replaced in the future with a SWISSGEO data pipeline.
"""

import json
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opensearchpy import helpers

from django.core.management.base import CommandError, CommandParser

from dataservice.models import Dataservice
from dataset.export_models import (
    LANGS,
    OARDataservice,
    OARDataset,
    OARDistribution,
)

# Base URLs are only needed to run the mapping code. In OpenSearch, the BaseURLs are not stored
from dataset.management.commands.oar_export import OAR_BASE_URL as _OAR_BASE_URL_BY_ENV
from dataset.management.commands.oar_export import OAS_BASE_URL as _OAS_BASE_URL_BY_ENV
from dataset.models import Dataset
from dataset.opensearch_helper import add_connection_arguments, build_client
from utils.command import CustomBaseCommand

# OpenSearch index names.
SERVICES_INDEX = "geoadmin-services"
# The datasets index is historically called `swissgeo-catalog` -- this matches the
# generated fixtures, the `swissgeo-catalog` links referenced by the other documents and
# the older tmp scripts. Its mapping file, however, is named `...swissgeo-datasets.json`.
DATASETS_INDEX = "swissgeo-catalog"
DISTRIBUTIONS_INDEX = "swissgeo-distributions"

# Index name -> mapping file.
_INDEXES_DIR = Path(__file__).parent / "opensearch-indexes"
INDEX_MAPPING_FILES = {
    SERVICES_INDEX: _INDEXES_DIR / "opensearch-index-mapping-geoadmin-services.json",
    DATASETS_INDEX: _INDEXES_DIR / "opensearch-index-mapping-swissgeo-datasets.json",
    DISTRIBUTIONS_INDEX: _INDEXES_DIR / "opensearch-index-mapping-swissgeo-distributions.json",
}

# Selectable record types -> target index.
TYPE_TO_INDEX = {
    "services": SERVICES_INDEX,
    "datasets": DATASETS_INDEX,
    "distributions": DISTRIBUTIONS_INDEX,
}

# OAR collection ids used when building records with the export models.
SERVICES_COLLECTION_ID = "geoadmin.services"
CATALOG_COLLECTION_ID = "swissgeo.catalog"

# OAR/OAS base URLs embedded in the record links while the OpenSearch documents are built, then
# stripped or rewritten to relative paths.
# The final documents never expose these, so which environment they come from doesn't affect the
# output -- 'prod' is hardcoded rather than exposed as an option.
OAR_BASE_URL = _OAR_BASE_URL_BY_ENV["prod"]
OAS_BASE_URL = _OAS_BASE_URL_BY_ENV["prod"]

OGC_SCHEMA = (
    "https://schemas.opengis.net/ogcapi/records/part1/1.0/openapi/schemas/recordGeoJSON.yaml"
)

# Language codes in the canonical order (de, fr, it, en).
LANG_CODES = list(LANGS.keys())

# How many superseded generations to keep around after a swap, so that a bad export can be
# rolled back by pointing the alias back at the previous index.
KEEP_GENERATIONS = 2


def _generation_index(alias: str, timestamp: datetime) -> str:
    """Build the concrete index name for a new generation of `alias`."""
    # Timestamp suffix appended to an alias to build a concrete index name, e.g.
    # `swissgeo-catalog-20260722153000`.
    timestamp_format = "%Y%m%d%H%M%S"
    return f"{alias}-{timestamp.strftime(timestamp_format)}"


def _is_generation_of(index: str, alias: str) -> bool:
    """Whether `index` is a timestamped generation of `alias` created by this command."""
    generation_regex = re.compile(r"-\d{14}$")
    return index.startswith(f"{alias}-") and bool(generation_regex.search(index))


def _alias_exists(client: Any, alias: str) -> bool:
    """Whether `alias` currently resolves to at least one index."""
    return bool(client.indices.exists_alias(name=alias))


def _create_action_removeindex(index: str, alias: str) -> dict:
    """Build the `_aliases` action detaching `index` from `alias`."""
    return {"remove": {"index": index, "alias": alias}}


def _create_action_addindex(index: str, alias: str) -> dict:
    """Build the `_aliases` action attaching `index` to `alias`."""
    return {"add": {"index": index, "alias": alias}}


def _dump(model: Any) -> dict:
    """Serialize an OAR export model to a plain dict (aliases applied, None fields dropped)."""
    return model.model_dump(exclude_none=True, by_alias=True)


def _clean_props(properties: dict, skip: frozenset[str] = frozenset()) -> dict:
    """Return a copy of a properties dict without `None` values and skipped keys.

    `model_dump(exclude_none=True)` drops None model *fields* but leaves None entries
    inside a plain `dict` field, so we strip them explicitly here.
    """
    return {k: v for k, v in properties.items() if v is not None and k not in skip}


def _rewrite_dist_links(
    links: list[dict], oar_base_url: str, oas_base_url: str, dataset_id: str
) -> list[dict]:
    """Rewrite a distribution feature's links into the OpenSearch form.

    The `dataset` and `dataservice` links are rewritten to relative
    `/collections/.../items/...` paths, the `styledby` link to the OAS style file is kept
    (with the per-language query/hreflang stripped, as styles are language-neutral), the
    intra-service `self`/`collection`/`alternate` links and any other OAR/OAS internal
    link without a defined mapping (e.g. `featureinfo`) are dropped, and genuinely external
    links are kept as-is.
    """
    rewritten: list[dict] = []
    for link in links:
        rel = link.get("rel", "")
        href = link.get("href", "")
        if rel in ("self", "collection", "alternate"):
            continue
        if rel == "dataset":
            rewritten.append(
                {
                    "href": f"/collections/{DATASETS_INDEX}/items/{dataset_id}",
                    "rel": "dataset",
                    "title": "Dataset Record",
                }
            )
        elif rel == "dataservice":
            # The href looks like `.../items/<service_id>?language=de`.
            service_id = href.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
            rewritten.append(
                {
                    "href": f"/collections/{SERVICES_INDEX}/items/{service_id}",
                    "rel": "dataservice",
                }
            )
        elif rel == "styledby":
            # Keep the style link, but drop the language-specific query/hreflang so it stays
            # language-neutral in the (multilingual) document.
            clean = {k: v for k, v in link.items() if k != "hreflang"}
            clean["href"] = href.split("?", 1)[0]
            rewritten.append(clean)
        elif href.startswith((oar_base_url, oas_base_url)):
            # Internal OAR/OAS link without a defined relative mapping -- drop it to keep the
            # document aligned with the OpenSearch format.
            continue
        else:
            rewritten.append(link)
    return rewritten


class Command(CustomBaseCommand):
    """Create the OpenSearch indices and import services/datasets/distributions documents."""

    help = "Export data entities (services, datasets, distributions) into OpenSearch"

    def add_arguments(self, parser: CommandParser) -> None:
        # Base class arguments (mainly '--logger').
        super().add_arguments(parser)

        add_connection_arguments(parser)

        parser.add_argument(
            "--keep-generations",
            type=int,
            default=KEEP_GENERATIONS,
            help=(
                f"Number of superseded indices to keep after a swap, for rollback "
                f"(default: {KEEP_GENERATIONS})"
            ),
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of documents per bulk request (default: 500)",
        )
        default_dump_dir = str(Path(".generated") / "oar_opensearch_export")
        parser.add_argument(
            "--dump",
            nargs="?",
            const=default_dump_dir,
            default=None,
            metavar="DIR",
            help=(
                "Write the generated documents to DIR/<index>/<id>.json instead of talking to "
                f"OpenSearch at all. DIR defaults to {default_dump_dir} when given without a value"
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        dump = options["dump"]

        self.print(f"Debug: parsed args = {json.dumps(options, default=str)}")

        # --dump never talks to OpenSearch at all; otherwise every run creates the indices,
        # imports the documents and atomically swaps the aliases over to the new generation.
        client = self.get_client(options) if not dump else None

        # alias -> concrete index the documents of this run go into. A non-dump run always builds
        # a fresh timestamped generation and swaps the aliases over once every type is imported.
        # For a dump run the aliases are only used to name the per-index output sub-directories.
        timestamp = datetime.now(UTC)
        targets = {
            index: (index if dump else _generation_index(index, timestamp))
            for index in TYPE_TO_INDEX.values()
        }

        if not dump:
            self.create_indexes(client, targets)

        for document_type, index in TYPE_TO_INDEX.items():
            self.import_documents(client, targets[index], document_type, options)

        if not dump:
            self.swap_aliases(client, targets, options)

        self.print_success("Done.")

    def get_client(self, options: dict) -> Any:  # pragma: no cover
        """Build and ping an OpenSearch client, optionally using AWS SigV4 auth."""
        return build_client(self, options)

    def create_indexes(self, client: Any, targets: dict[str, str]) -> None:
        """Create the target index of each alias in `targets`.

        The targets are new timestamped generations that cannot exist yet, so they are simply
        created.
        """
        for alias, index in targets.items():
            self.print_success(f"Creating index '{index}'")
            # The mapping files are keyed by alias, not by the timestamped generation name.
            client.indices.create(
                index=index, body=json.loads(INDEX_MAPPING_FILES[alias].read_text())
            )

    def import_documents(self, client: Any, index: str, document_type: str, options: dict) -> None:
        """Build the documents of type `document_type` and index them into `index`.

        Args:
            client (Any): The OpenSearch client, or None on a `--dump` run, where it is unused.
            index (str): The opensearch index to index into (i.e. 'swissgeo-catalog-20260722153000')
                         does not matter for `--dump`.
            document_type (str): Which type export ('services', 'datasets' or 'distributions')
            options (dict): The parsed command options. `dump` and `batch_size` are used here.
        """
        self.print_success(f"Building {document_type} documents...")
        documents = self.build_documents(document_type)

        if options["dump"]:
            self.dump_to_files(documents, TYPE_TO_INDEX[document_type], Path(options["dump"]))
            self.print_success(f"Generated {len(documents)}! (not imported).")
            return

        def actions() -> Iterator[dict]:
            for doc in documents:
                yield {"_index": index, "_id": doc["id"], "_source": doc}

        self.print_success(f"Indexing {len(documents)} documents into '{index}'")
        ok, errors = helpers.bulk(
            client,
            actions(),
            chunk_size=options["batch_size"],
            raise_on_error=False,
        )
        if errors:
            self.print_error(f"{len(errors)} errors while indexing into '{index}':")
            for err in errors[:5]:
                self.print_error(f"  {err}")
            # Abort rather than let a partially indexed generation reach the alias swap. The
            # new indices are left behind for inspection; the aliases still point at the
            # previous generation, so readers are unaffected.
            raise CommandError(f"{len(errors)} documents failed to index into '{index}'")
        self.print_success(f"{ok} documents indexed into '{index}'")

    def swap_aliases(self, client: Any, targets: dict[str, str], options: dict) -> None:
        """Point every alias in `targets` at its freshly built index, atomically.

        All removes and adds go into a single `_aliases` request, which OpenSearch applies as
        one cluster state update. Searches therefore switch from the old to the new generation
        between two requests, with no window in which an alias is missing, resolves to both
        generations at once, or -- across the three indices -- mixes generations.
        """
        # Bulk-indexed documents only become searchable on the next refresh (1s by default).
        # Without this the alias would swap to an index whose documents are still invisible,
        # and searches would briefly return no results -- exactly the downtime we are avoiding.
        self.print_success("Refreshing new indices before the swap")
        client.indices.refresh(index=",".join(targets.values()))

        # An alias cannot share a name with a concrete index. If one of the alias names is still a
        # concrete index (an unexpected state now that we only ever work with aliases/generations),
        # the atomic swap cannot proceed -- fail loudly instead of silently doing something wrong.
        blocking = [
            alias
            for alias in targets
            if client.indices.exists(index=alias) and not _alias_exists(client, alias)
        ]
        if blocking:
            names = ", ".join(f"'{a}'" for a in blocking)
            subject = (
                f"{names} is a concrete index"
                if len(blocking) == 1
                else (f"{names} are concrete indices")
            )
            raise CommandError(
                f"{subject}, not an alias, so the new index cannot be swapped in atomically. "
                f"Delete it manually and re-run."
            )

        actions: list[dict] = []

        # Collect the indexes this swap detaches, so they can be removed from the alias.
        #
        # Example:
        # new index: swissgeo-distributions-2026002
        # old index: swissgeo-distributions-2026001
        # alias swissgeo-distributions: action remove index : swissgeo-distributions-2026001
        #                               action add index    : swissgeo-distributions-2026002
        superseded: dict[str, list[str]] = {}
        for alias, index in targets.items():
            old = []
            if _alias_exists(client, alias):
                old = sorted(client.indices.get_alias(name=alias))
            superseded[alias] = [i for i in old if i != index]
            actions += [_create_action_removeindex(i, alias) for i in superseded[alias]]
            actions.append(_create_action_addindex(index, alias))

        client.indices.update_aliases(body={"actions": actions})
        for alias, index in targets.items():
            previous = ", ".join(superseded[alias]) or "none"
            self.print_success(f"Alias '{alias}' -> '{index}' (was: {previous})")

        self.prune_generations(client, targets, options["keep_generations"])

    def prune_generations(self, client: Any, targets: dict[str, str], keep: int) -> None:
        """Delete old generations of each alias, keeping the `keep` most recent for rollback.

        The candidates are discovered from the cluster rather than from what the alias pointed
        at, because a swap detaches the previous generation: after the second run the alias only
        ever names one old index, and every generation before it would otherwise be orphaned and
        never cleaned up.

        Only indices this command created (`<alias>-<timestamp>`) are considered, so an
        unrelated index that happens to share the alias prefix is left alone. Timestamped names
        sort chronologically, so the tail of the sorted list is the most recent.
        """

        # If `keep` is negative, don't prune anything (keep everything).
        if keep < 0:
            return

        for alias, index in targets.items():
            existing = client.indices.get(index=f"{alias}-*", ignore_unavailable=True)
            # Never touch the generation just swapped in, whatever `keep` says.
            candidates = sorted(i for i in existing if i != index and _is_generation_of(i, alias))
            # Keep the `keep` newest (the tail of the sorted list); everything older is stale.
            prune_count = len(candidates) - keep
            if prune_count <= 0:
                continue
            to_prune = candidates[:prune_count]
            for old_index in to_prune:
                self.print(f"Deleting old index '{old_index}'")
                client.indices.delete(index=old_index)

    def dump_to_files(self, documents: list[dict], index: str, dump_dir: Path) -> None:
        """Write each document as its own JSON file below `dump_dir`."""
        target_dir = dump_dir / index
        target_dir.mkdir(parents=True, exist_ok=True)

        for doc in documents:
            # Document ids are slugs, but keep the path confined to target_dir regardless.
            filename = Path(str(doc["id"])).name
            path = target_dir / f"{filename}.json"
            path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            self.print("Wrote %s", path)

        self.print_success(f"Wrote {len(documents)} documents to {target_dir}")

    def build_documents(self, document_type: str) -> list[dict]:
        documents: list[dict] = []
        if document_type == "services":
            for service in Dataservice.objects.all():
                self.print(f" - {service.dataservice_id}")
                documents.append(self.build_service_doc(service, OAR_BASE_URL))
        elif document_type == "datasets":
            for dataset in Dataset.objects.all():
                self.print(f" - {dataset.dataset_id}")
                documents.append(self.build_dataset_doc(dataset, OAR_BASE_URL))
        elif document_type == "distributions":
            for dataset in Dataset.objects.all():
                self.print(f" - {dataset.dataset_id}")
                documents.append(self.build_distribution_doc(dataset, OAR_BASE_URL, OAS_BASE_URL))
        return documents

    def build_service_doc(self, service: Dataservice, oar_base_url: str) -> dict:
        """Build a `geoadmin-services` document from a Dataservice."""
        features = {
            lang: _dump(
                OARDataservice.from_dataservice(service, lang, SERVICES_COLLECTION_ID, oar_base_url)
            )
            for lang in LANG_CODES
        }
        base = features["de"]
        # Keep the (de) self/collection links and external links; drop the per-language
        # 'alternate' self links.
        links = [link for link in base["links"] if link.get("rel") != "alternate"]
        return {
            "id": base["id"],
            "type": base["type"],
            "links": links,
            "properties": {
                "type": base["properties"].get("type"),
                "title": {
                    lang: features[lang]["properties"].get("title") or "" for lang in LANG_CODES
                },
            },
            "linkTemplates": base.get("linkTemplates", []),
        }

    def build_dataset_doc(self, dataset: Dataset, oar_base_url: str) -> dict:
        """Build a `swissgeo-catalog` document from a Dataset."""
        features = {
            lang: _dump(OARDataset.from_dataset(dataset, lang, CATALOG_COLLECTION_ID, oar_base_url))
            for lang in LANG_CODES
        }
        base = features["de"]

        # Keep external links only (drop OAR self/alternate/collection/items links), then add
        # the link to the distributions collection in the OpenSearch (relative) form.
        links = [
            link for link in base["links"] if not link.get("href", "").startswith(oar_base_url)
        ]
        links.append(
            {
                "href": f"/collections/{DISTRIBUTIONS_INDEX}/items/{base['id']}",
                "rel": "distributions",
                "title": "Distributions",
            }
        )

        properties = _clean_props(
            base["properties"], skip=frozenset({"title", "description", "language"})
        )
        properties["title"] = {
            lang: features[lang]["properties"].get("title") or "" for lang in LANG_CODES
        }
        properties["description"] = {
            lang: features[lang]["properties"].get("description") or "" for lang in LANG_CODES
        }

        return {
            "$schema": OGC_SCHEMA,
            "id": base["id"],
            "type": base["type"],
            "geometry": base.get("geometry"),
            "links": links,
            "properties": properties,
        }

    def build_distribution_doc(
        self, dataset: Dataset, oar_base_url: str, oas_base_url: str
    ) -> dict:
        """Build a `swissgeo-distributions` FeatureCollection document from a Dataset."""
        collection_id = f"{dataset.dataset_id}.distributions"
        features = []
        for distribution in dataset.distribution_set.all():  # ty:ignore[unresolved-attribute]
            per_lang = {
                lang: _dump(
                    OARDistribution.from_distribution(
                        distribution, lang, collection_id, oar_base_url, oas_base_url
                    )
                )
                for lang in LANG_CODES
            }
            feature = per_lang["de"]
            feature["links"] = _rewrite_dist_links(
                feature.get("links", []), oar_base_url, oas_base_url, dataset.dataset_id
            )
            # Turn the translated fields into {lang: value} objects.
            feature["properties"]["title"] = {
                lang: per_lang[lang]["properties"].get("title") or "" for lang in LANG_CODES
            }
            descriptions = {
                lang: per_lang[lang]["properties"].get("description") or "" for lang in LANG_CODES
            }
            if any(descriptions.values()):
                feature["properties"]["description"] = descriptions
            features.append(feature)

        return {
            "id": dataset.dataset_id,
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "title": {
                    lang: getattr(dataset, f"title_short_{lang}", None) or "" for lang in LANG_CODES
                },
            },
        }
