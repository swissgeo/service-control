"""Static checks on the OpenSearch index mapping files."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

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


@pytest.mark.parametrize("mapping_file", MAPPING_FILES, ids=lambda p: p.name)
def test_text_fields_are_accent_insensitive(mapping_file: Path) -> None:
    """Every searchable text field must fold accents at index and search time.

    Otherwise a query for 'arret' does not find 'Arrêt' (and 'zurich' does not find 'Zürich').
    """
    mapping = json.loads(mapping_file.read_text())
    analyzers = mapping.get("settings", {}).get("analysis", {}).get("analyzer", {})

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


@pytest.mark.parametrize("mapping_file", MAPPING_FILES, ids=lambda p: p.name)
def test_german_analyzers_fold_after_normalization(mapping_file: Path) -> None:
    """asciifolding must run after german_decompound and german_normalization.

    Folding before the decompounder breaks word-list entries like 'fläche'; folding before
    german_normalization prevents its 'ue' -> 'u' rule ('zuerich' -> 'zurich').
    """
    analyzers = (
        json.loads(mapping_file.read_text())
        .get("settings", {})
        .get("analysis", {})
        .get("analyzer", {})
    )
    for name in ("german_decompound", "german_search"):
        if name not in analyzers:
            continue
        filters = analyzers[name]["filter"]
        assert filters[-1] == "asciifolding", f"{mapping_file.name}: {name} filters {filters}"
        assert filters.index("german_normalization") < filters.index("asciifolding")
