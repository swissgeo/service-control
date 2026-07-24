"""Tests for the atomic alias swap of the OpenSearch export command."""

from datetime import UTC, datetime
from typing import Any

from django.core.management.base import CommandError

import pytest

from dataset.management.commands.oar_opensearch_export import (
    Command,
    _generation_index,
    _is_generation_of,
)


class FakeIndices:
    """Minimal stand-in for ``client.indices`` backed by an alias -> indices mapping."""

    def __init__(self, aliases: dict[str, list[str]], concrete: list[str] | None = None) -> None:
        # alias name -> the concrete indices it points at
        self.aliases = {a: list(i) for a, i in aliases.items()}
        # indices that exist without being (or being behind) an alias
        self.concrete = set(concrete or [])
        for indices in self.aliases.values():
            self.concrete.update(indices)
        self.update_alias_calls: list[list[dict]] = []
        self.deleted: list[str] = []
        self.refreshed: list[str] = []

    def exists(self, index: str) -> bool:
        return index in self.concrete or index in self.aliases

    def exists_alias(self, name: str) -> bool:
        return name in self.aliases

    def get_alias(self, name: str) -> dict[str, Any]:
        if name not in self.aliases:
            raise AssertionError(f"get_alias called for missing alias {name!r}")
        return {index: {"aliases": {name: {}}} for index in self.aliases[name]}

    def get(self, index: str, ignore_unavailable: bool = False) -> dict[str, Any]:  # noqa: ARG002
        """Resolve a trailing-wildcard index pattern against the existing concrete indices."""
        if not index.endswith("*"):
            raise AssertionError(f"FakeIndices.get only supports wildcards, got {index!r}")
        prefix = index[:-1]
        return {i: {} for i in sorted(self.concrete) if i.startswith(prefix)}

    def refresh(self, index: str) -> None:
        self.refreshed.append(index)

    def delete(self, index: str) -> None:
        self.deleted.append(index)
        self.concrete.discard(index)
        self.aliases.pop(index, None)

    def update_aliases(self, body: dict) -> None:
        self.update_alias_calls.append(body["actions"])
        for action in body["actions"]:
            if "remove" in action:
                spec = action["remove"]
                self.aliases.get(spec["alias"], []).remove(spec["index"])
            else:
                spec = action["add"]
                self.aliases.setdefault(spec["alias"], []).append(spec["index"])


class FakeClient:
    def __init__(self, aliases: dict[str, list[str]], concrete: list[str] | None = None) -> None:
        self.indices = FakeIndices(aliases, concrete)


def _command() -> Command:
    command = Command()
    # print()/print_success() read verbosity and logger off self.options, which is normally
    # populated by execute().
    command.options = {"verbosity": 0, "logger": False}
    return command


def _options(**overrides: Any) -> dict:
    options = {"keep_generations": 2}
    options.update(overrides)
    return options


def test_generation_index_and_detection():
    timestamp = datetime(2026, 7, 22, 15, 30, 0, tzinfo=UTC)
    index = _generation_index("swissgeo-catalog", timestamp)

    assert index == "swissgeo-catalog-20260722153000"
    assert _is_generation_of(index, "swissgeo-catalog")
    # The alias itself and unrelated/untimestamped indices are not generations.
    assert not _is_generation_of("swissgeo-catalog", "swissgeo-catalog")
    assert not _is_generation_of("swissgeo-catalog-backup", "swissgeo-catalog")
    assert not _is_generation_of("geoadmin-services-20260722153000", "swissgeo-catalog")


def test_swap_moves_every_alias_in_a_single_request():
    client = FakeClient(
        {
            "swissgeo-catalog": ["swissgeo-catalog-20260722100000"],
            "geoadmin-services": ["geoadmin-services-20260722100000"],
        }
    )
    targets = {
        "swissgeo-catalog": "swissgeo-catalog-20260722153000",
        "geoadmin-services": "geoadmin-services-20260722153000",
    }

    _command().do_swap_aliases(client, targets, _options())

    # One _aliases call for both indices: that is what makes the swap atomic across them.
    assert len(client.indices.update_alias_calls) == 1
    actions = client.indices.update_alias_calls[0]
    assert actions == [
        {"remove": {"index": "swissgeo-catalog-20260722100000", "alias": "swissgeo-catalog"}},
        {"add": {"index": "swissgeo-catalog-20260722153000", "alias": "swissgeo-catalog"}},
        {"remove": {"index": "geoadmin-services-20260722100000", "alias": "geoadmin-services"}},
        {"add": {"index": "geoadmin-services-20260722153000", "alias": "geoadmin-services"}},
    ]
    assert client.indices.aliases["swissgeo-catalog"] == ["swissgeo-catalog-20260722153000"]
    # Only one generation was superseded, which is below --keep-generations, so nothing is
    # deleted yet.
    assert client.indices.deleted == []


def test_swap_creates_alias_when_none_exists():
    client = FakeClient({})
    targets = {"swissgeo-catalog": "swissgeo-catalog-20260722153000"}

    _command().do_swap_aliases(client, targets, _options())

    assert client.indices.update_alias_calls == [
        [{"add": {"index": "swissgeo-catalog-20260722153000", "alias": "swissgeo-catalog"}}]
    ]
    assert client.indices.deleted == []


def test_swap_refuses_concrete_index():
    client = FakeClient({}, concrete=["swissgeo-catalog"])
    targets = {"swissgeo-catalog": "swissgeo-catalog-20260722153000"}

    with pytest.raises(CommandError, match="is a concrete index, not an alias"):
        _command().do_swap_aliases(client, targets, _options())

    # Nothing was touched -- the old index still serves reads.
    assert client.indices.deleted == []
    assert client.indices.update_alias_calls == []


def test_swap_refuses_concrete_index_before_touching_other_aliases():
    """A concrete index under any alias name aborts the swap before any alias is moved."""
    client = FakeClient(
        {"geoadmin-services": ["geoadmin-services-20260722100000"]},
        concrete=["swissgeo-catalog"],
    )
    targets = {
        "geoadmin-services": "geoadmin-services-20260722153000",
        "swissgeo-catalog": "swissgeo-catalog-20260722153000",
    }

    with pytest.raises(CommandError):
        _command().do_swap_aliases(client, targets, _options())

    assert client.indices.deleted == []
    assert client.indices.update_alias_calls == []


def test_prune_keeps_the_configured_number_of_generations():
    """Generations detached by *earlier* swaps are pruned too, not just the current one.

    Only the newest old index is still behind the alias; the rest are orphans left over from
    previous runs, and they are exactly what pruning has to catch.
    """
    client = FakeClient(
        {"swissgeo-catalog": ["swissgeo-catalog-20260722130000"]},
        concrete=[
            "swissgeo-catalog-20260722100000",
            "swissgeo-catalog-20260722110000",
            "swissgeo-catalog-20260722120000",
        ],
    )
    targets = {"swissgeo-catalog": "swissgeo-catalog-20260722153000"}

    _command().do_swap_aliases(client, targets, _options(keep_generations=2))

    # Four old generations exist, the two most recent stay available for a rollback.
    assert client.indices.deleted == [
        "swissgeo-catalog-20260722100000",
        "swissgeo-catalog-20260722110000",
    ]


def test_prune_never_deletes_the_generation_just_swapped_in():
    client = FakeClient({"swissgeo-catalog": ["swissgeo-catalog-20260722100000"]})
    targets = {"swissgeo-catalog": "swissgeo-catalog-20260722153000"}

    _command().do_swap_aliases(client, targets, _options(keep_generations=0))

    assert client.indices.deleted == ["swissgeo-catalog-20260722100000"]
    assert client.indices.aliases["swissgeo-catalog"] == ["swissgeo-catalog-20260722153000"]


def test_prune_never_deletes_indices_it_did_not_create():
    """An index sharing the alias prefix but not ``<alias>-<timestamp>`` is left alone."""
    client = FakeClient(
        {"swissgeo-catalog": ["swissgeo-catalog-20260722120000"]},
        concrete=[
            "swissgeo-catalog-manual-backup",
            "swissgeo-catalog-20260722100000",
            "swissgeo-catalog-20260722110000",
        ],
    )
    targets = {"swissgeo-catalog": "swissgeo-catalog-20260722153000"}

    _command().do_swap_aliases(client, targets, _options(keep_generations=1))

    assert client.indices.deleted == [
        "swissgeo-catalog-20260722100000",
        "swissgeo-catalog-20260722110000",
    ]
    assert "swissgeo-catalog-manual-backup" not in client.indices.deleted


def test_swap_refreshes_new_indices_before_moving_the_alias():
    """Without a refresh the alias would briefly point at documents that are not searchable."""
    client = FakeClient({"swissgeo-catalog": ["swissgeo-catalog-20260722100000"]})
    targets = {"swissgeo-catalog": "swissgeo-catalog-20260722153000"}

    _command().do_swap_aliases(client, targets, _options())

    assert client.indices.refreshed == ["swissgeo-catalog-20260722153000"]
