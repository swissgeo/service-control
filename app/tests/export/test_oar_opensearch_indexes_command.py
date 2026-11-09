"""Tests for the operational `oar_opensearch_indexes` command."""

from io import StringIO
from typing import Any
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

CATALOG = "swissgeo-catalog"
OLDEST = f"{CATALOG}-20260720000000"
PREVIOUS = f"{CATALOG}-20260721000000"
CURRENT = f"{CATALOG}-20260722000000"
NEWER = f"{CATALOG}-20260723000000"
SERVICES = "geoadmin-services"
SERVICES_PREVIOUS = f"{SERVICES}-20260721000000"
SERVICES_CURRENT = f"{SERVICES}-20260722000000"


class FakeIndices:
    """A small model of the cluster: index name -> aliases and document count."""

    def __init__(self, client: FakeClient) -> None:
        self.client = client
        self.deleted: list[str] = []
        self.alias_requests: list[list[dict]] = []
        self.cloned: list[tuple[str, str]] = []

    def match(self, expression: str) -> dict[str, list[str]]:
        def matches(part: str, index: str, aliases: list[str]) -> bool:
            if part in ("*", "_all") or index == part or part in aliases:
                return True
            return part.endswith("*") and index.startswith(part[:-1])

        return {
            index: aliases
            for index, aliases in self.client.aliases.items()
            if any(matches(part, index, aliases) for part in expression.split(","))
        }

    def get(self, index: str, ignore_unavailable: bool = False) -> dict[str, Any]:  # noqa: ARG002
        return {
            name: {"aliases": {alias: {} for alias in aliases}}
            for name, aliases in self.match(index).items()
        }

    def exists(self, index: str) -> bool:
        return bool(self.match(index))

    def exists_alias(self, name: str) -> bool:
        return any(name in aliases for aliases in self.client.aliases.values())

    def get_alias(self, name: str) -> dict[str, Any]:
        return {i: {} for i, aliases in self.client.aliases.items() if name in aliases}

    def update_aliases(self, body: dict) -> None:
        self.alias_requests.append(body["actions"])

    def delete(self, index: str) -> None:
        self.deleted.append(index)
        del self.client.aliases[index]

    def put_settings(self, index: str, body: dict) -> None:
        pass

    def clone(self, index: str, target: str) -> None:
        self.cloned.append((index, target))


class FakeClient:
    def __init__(self, aliases: dict[str, list[str]], counts: dict[str, int] | None = None) -> None:
        self.aliases = aliases
        self.counts = counts or {}
        self.indices = FakeIndices(self)

    def count(self, index: str) -> dict[str, int]:
        indices = self.indices.match(index)
        return {"count": sum(self.counts.get(name, 10) for name in indices)}


def _cluster(counts: dict[str, int] | None = None) -> FakeClient:
    return FakeClient(
        {
            OLDEST: [],
            PREVIOUS: [],
            CURRENT: [CATALOG],
            NEWER: [],
            SERVICES_PREVIOUS: [],
            SERVICES_CURRENT: [SERVICES],
            f"{CATALOG}-backup": [],
            "unrelated": [],
        },
        counts,
    )


def _run(client: FakeClient, *args: str) -> str:
    out = StringIO()
    with patch("export.management.commands.oar_opensearch_indexes.build_client") as build_client:
        build_client.return_value = client
        call_command("oar_opensearch_indexes", *args, stdout=out)
    return out.getvalue()


def _move(alias: str, old: str, new: str) -> list[dict]:
    return [{"remove": {"index": old, "alias": alias}}, {"add": {"index": new, "alias": alias}}]


def test_rollback_moves_alias_to_previous_generation_atomically():
    client = _cluster({CURRENT: 100, PREVIOUS: 90})

    output = _run(client, "rollback", CATALOG)

    # NEWER is a generation already rolled back from or a failed run, and must not be picked.
    assert client.indices.alias_requests == [_move(CATALOG, CURRENT, PREVIOUS)]
    assert f"'{CURRENT}' (100 documents) -> '{PREVIOUS}' (90 documents)" in output


def test_rollback_moves_several_aliases_in_a_single_request():
    client = _cluster()

    _run(client, "rollback", CATALOG, SERVICES, CATALOG)

    assert client.indices.alias_requests == [
        _move(CATALOG, CURRENT, PREVIOUS) + _move(SERVICES, SERVICES_CURRENT, SERVICES_PREVIOUS)
    ]


def test_rollback_dry_run_changes_nothing():
    client = _cluster()

    output = _run(client, "rollback", CATALOG, "--dry-run")

    assert client.indices.alias_requests == []
    assert f"Would move Alias '{CATALOG}'" in output


def test_rollback_to_named_generation():
    client = _cluster()

    _run(client, "rollback", CATALOG, "--to", OLDEST)

    assert client.indices.alias_requests == [_move(CATALOG, CURRENT, OLDEST)]


@pytest.mark.parametrize(
    ("to", "message"),
    [
        (CURRENT, "already points at"),
        (SERVICES_CURRENT, "not an existing generation"),
        (f"{CATALOG}-backup", "not an existing generation"),
        (f"{CATALOG}-19990101000000", "not an existing generation"),
    ],
)
def test_rollback_rejects_invalid_target(to, message):
    client = _cluster()

    with pytest.raises(CommandError, match=message):
        _run(client, "rollback", CATALOG, "--to", to)

    assert client.indices.alias_requests == []


def test_rollback_to_needs_a_single_alias():
    with pytest.raises(CommandError, match="single alias"):
        _run(_cluster(), "rollback", CATALOG, SERVICES, "--to", OLDEST)


def test_rollback_refuses_unknown_alias():
    with pytest.raises(CommandError, match="invalid choice"):
        _run(_cluster(), "rollback", "*")


def test_rollback_without_alias_in_cluster():
    client = FakeClient({OLDEST: []})

    with pytest.raises(CommandError, match="not an alias"):
        _run(client, "rollback", CATALOG)


def test_rollback_without_older_generation():
    client = FakeClient({CURRENT: [CATALOG]})

    with pytest.raises(CommandError, match="no generation older"):
        _run(client, "rollback", CATALOG)


def test_rollback_from_non_generation_needs_explicit_target():
    client = FakeClient({f"{CATALOG}-renamed": [CATALOG], PREVIOUS: []})

    with pytest.raises(CommandError, match="not a generation"):
        _run(client, "rollback", CATALOG)

    _run(client, "rollback", CATALOG, "--to", PREVIOUS)
    assert client.indices.alias_requests == [_move(CATALOG, f"{CATALOG}-renamed", PREVIOUS)]


def test_rollback_refuses_empty_generation_and_moves_nothing():
    client = _cluster({SERVICES_PREVIOUS: 0})

    with pytest.raises(CommandError, match="is empty"):
        _run(client, "rollback", CATALOG, SERVICES)

    assert client.indices.alias_requests == []


def test_delete_unserved_index():
    client = _cluster()

    _run(client, "delete", OLDEST)

    assert client.indices.deleted == [OLDEST]


def test_delete_refuses_served_index():
    client = _cluster()

    with pytest.raises(CommandError, match="--force"):
        _run(client, "delete", CURRENT)

    assert client.indices.deleted == []


def test_delete_refuses_alias_name_resolving_to_served_index():
    client = _cluster()

    with pytest.raises(CommandError, match="--force"):
        _run(client, "delete", CATALOG)

    assert client.indices.deleted == []


def test_delete_served_index_with_force():
    client = _cluster()

    _run(client, "delete", CURRENT, "--force")

    assert client.indices.deleted == [CURRENT]


@pytest.mark.parametrize("pattern", ["*", f"{CATALOG}-2026*", "_all", f"{OLDEST},{CATALOG}-2*"])
def test_delete_refuses_wildcard(pattern):
    client = _cluster()

    with pytest.raises(CommandError, match="--allow-wildcard"):
        _run(client, "delete", pattern)

    assert client.indices.deleted == []


def test_delete_wildcard_with_acknowledgment_still_spares_served_indices():
    client = _cluster()

    with pytest.raises(CommandError, match="--force"):
        _run(client, "delete", f"{CATALOG}-2026*", "--allow-wildcard")

    assert client.indices.deleted == []


def test_delete_wildcard_with_both_flags():
    client = _cluster()

    _run(client, "delete", f"{CATALOG}-2026*", "--allow-wildcard", "--force")

    assert client.indices.deleted == [OLDEST, PREVIOUS, CURRENT, NEWER]


def test_delete_a_refused_index_blocks_the_whole_run():
    client = _cluster()

    with pytest.raises(CommandError, match="--force"):
        _run(client, "delete", OLDEST, CURRENT)

    assert client.indices.deleted == []


def test_delete_dry_run_previews_matches_and_refusals():
    client = _cluster()

    output = _run(client, "delete", f"{CATALOG}-2026*", "--dry-run")

    assert client.indices.deleted == []
    assert f"Would delete '{CURRENT}'" in output
    assert f"Would refuse: {CATALOG}-2026* needs --allow-wildcard" in output
    assert f"Would refuse: '{CURRENT}' is still behind alias {CATALOG}" in output


def test_delete_no_match():
    with pytest.raises(CommandError, match="No index matches"):
        _run(_cluster(), "delete", "missing")


@pytest.mark.parametrize("target", ["copy-*", "copy-?", "_all"])
def test_rename_refuses_wildcard_target(target):
    client = _cluster()

    with pytest.raises(CommandError, match="is a wildcard"):
        _run(client, "rename", OLDEST, target)

    assert client.indices.cloned == []


def test_rename_refuses_wildcard_source():
    with pytest.raises(CommandError, match="is a wildcard"):
        _run(_cluster(), "rename", f"{CATALOG}-*", "copy")


def test_rename_clones_to_valid_target():
    client = _cluster()

    _run(client, "rename", OLDEST, "copy")

    assert client.indices.cloned == [(OLDEST, "copy")]
    assert client.indices.deleted == [OLDEST]


def test_list_shows_only_generations_by_default():
    output = _run(_cluster(), "list")

    assert OLDEST in output
    assert f"{CURRENT}  <- {CATALOG}" in output
    assert f"{CATALOG}-backup" not in output
    assert "unrelated" not in output


def test_list_keeps_served_and_blocking_indices_visible():
    client = FakeClient({f"{CATALOG}-renamed": [CATALOG], SERVICES: []})

    output = _run(client, "list")

    assert f"{CATALOG}-renamed" in output
    assert f"{SERVICES}\n" in output


def test_list_all_shows_everything():
    output = _run(_cluster(), "list", "--all")

    assert f"{CATALOG}-backup" in output
    assert "unrelated" in output


def test_list_with_only_unmanaged_matches_reports_none():
    output = _run(FakeClient({f"{CATALOG}-backup": []}), "list")

    assert "No indices found." in output
