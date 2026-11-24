"""Static checks on the OpenSearch index mapping files."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from export.export_models import LANGS
from export.management.commands.oar_opensearch_export import (
    INDEX_ANALYSIS_FILE,
    INDEX_MAPPING_FILES,
    load_index_definition,
)

MAPPINGS_DIR = (
    Path(__file__).resolve().parents[2]
    / "export"
    / "management"
    / "commands"
    / "opensearch-indexes"
)
MAPPING_FILES = sorted(MAPPINGS_DIR.glob("opensearch-index-mapping-*.json"))


def _text_fields(node: dict[str, Any], path: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield (path, field definition) for every analyzed text field in a mapping."""
    for key, value in node.items():
        if not isinstance(value, dict):
            continue
        if value.get("type") in ("text", "search_as_you_type"):
            yield f"{path}.{key}".lstrip("."), value
        yield from _text_fields(value, f"{path}.{key}")


def test_mapping_files_found() -> None:
    assert MAPPING_FILES, f"no mapping files found in {MAPPINGS_DIR}"
    assert sorted(INDEX_MAPPING_FILES.values()) == MAPPING_FILES


@pytest.mark.parametrize("mapping_file", MAPPING_FILES, ids=lambda p: p.name)
def test_analysis_comes_from_the_shared_file(mapping_file: Path) -> None:
    """A copy of the analysis block in a mapping file would silently replace the shared one."""
    mapping = json.loads(mapping_file.read_text())
    assert "analysis" not in mapping.get("settings", {})


@pytest.mark.parametrize("alias", INDEX_MAPPING_FILES)
def test_index_definition_merges_mapping_and_analysis(alias: str) -> None:
    definition = load_index_definition(alias)
    mapping = json.loads(INDEX_MAPPING_FILES[alias].read_text())

    assert definition["settings"]["analysis"] == json.loads(INDEX_ANALYSIS_FILE.read_text())
    assert definition["mappings"] == mapping["mappings"]
    # Settings that are specific to an index survive the merge.
    for name, value in mapping.get("settings", {}).items():
        assert definition["settings"][name] == value


@pytest.mark.parametrize("mapping_file", MAPPING_FILES, ids=lambda p: p.name)
def test_mapping_is_strict_for_all_languages(mapping_file: Path) -> None:
    """An unknown field has to fail the export, at the root and in every language subtree."""
    mappings = json.loads(mapping_file.read_text())["mappings"]

    assert mappings["dynamic"] == "strict"
    assert set(mappings["properties"]) == {"id", "type", *LANGS}
    for lang in LANGS:
        assert mappings["properties"][lang]["dynamic"] == "strict", lang


@pytest.mark.parametrize("mapping_file", MAPPING_FILES, ids=lambda p: p.name)
def test_languages_map_the_same_fields(mapping_file: Path) -> None:
    """service-oa-records reads the fields of every language from a single subtree."""
    properties = json.loads(mapping_file.read_text())["mappings"]["properties"]
    fields = {
        lang: sorted(properties[lang]["properties"]["properties"]["properties"]) for lang in LANGS
    }

    assert all(names == fields["de"] for names in fields.values()), fields


@pytest.mark.parametrize("mapping_file", MAPPING_FILES, ids=lambda p: p.name)
def test_text_fields_are_accent_insensitive(mapping_file: Path) -> None:
    """Every searchable text field must fold accents at index and search time.

    Otherwise a query for 'arret' does not find 'Arrêt' (and 'zurich' does not find 'Zürich').
    """
    mapping = json.loads(mapping_file.read_text())
    analyzers = json.loads(INDEX_ANALYSIS_FILE.read_text())["analyzer"]

    for path, field in _text_fields(mapping["mappings"]):
        # 'keyword' analyzer fields (e.g. concepts) are exact-match by design
        if field.get("analyzer") == "keyword":
            continue
        for role in ("analyzer", "search_analyzer"):
            # search_analyzer falls back to analyzer when not set
            name = field.get(role, field.get("analyzer"))
            assert name, (
                f"{mapping_file.name}: {path} uses the default analyzer (no accent folding)"
            )
            assert name in analyzers, f"{mapping_file.name}: {path} {role} {name!r} is not defined"
            assert "asciifolding" in analyzers[name]["filter"], (
                f"{mapping_file.name}: {path} {role} {name!r} lacks 'asciifolding'"
            )


def test_german_analyzers_fold_after_normalization() -> None:
    """asciifolding must run after german_decompound and german_normalization.

    Folding before the decompounder breaks word-list entries like 'fläche'; folding before
    german_normalization prevents its 'ue' -> 'u' rule ('zuerich' -> 'zurich').
    """
    analyzers = json.loads(INDEX_ANALYSIS_FILE.read_text())["analyzer"]
    for name in ("german_decompound", "german_search"):
        filters = analyzers[name]["filter"]
        assert filters[-1] == "asciifolding", f"{name} filters {filters}"
        assert filters.index("german_normalization") < filters.index("asciifolding")
