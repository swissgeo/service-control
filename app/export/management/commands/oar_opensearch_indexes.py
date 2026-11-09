"""List, roll back, rename and delete the OpenSearch indices backing the OGC API Records search.

This is an operational companion to `oar_opensearch_export`: that command creates timestamped
generations and swaps the aliases over, this one lets you inspect what is currently in the
cluster, point an alias back at an older generation, rename an index and remove indices that are
no longer wanted.

    manage.py oar_opensearch_indexes list
    manage.py oar_opensearch_indexes list --all
    manage.py oar_opensearch_indexes rollback swissgeo-catalog --dry-run
    manage.py oar_opensearch_indexes rollback swissgeo-catalog swissgeo-distributions
    manage.py oar_opensearch_indexes rollback swissgeo-catalog --to swissgeo-catalog-20260722100000
    manage.py oar_opensearch_indexes delete swissgeo-catalog-20260722100000
    manage.py oar_opensearch_indexes delete 'swissgeo-catalog-2026*' --dry-run
    manage.py oar_opensearch_indexes delete 'swissgeo-catalog-2026*' --allow-wildcard
    manage.py oar_opensearch_indexes rename swissgeo-catalog-20260722100000 \
        swissgeo-catalog-20260722100001

Deletion has no confirmation prompt, so it refuses the two dangerous cases unless told otherwise:
wildcard patterns need `--allow-wildcard`, and indices still behind an alias (serving live search
results) need `--force`. If either check fails, nothing is deleted. Use `--dry-run` first.
"""

from typing import Any

from django.core.management.base import CommandError, CommandParser

from export.management.commands.oar_opensearch_export import (
    TYPE_TO_INDEX,
    _alias_exists,
    _is_generation_of,
)
from export.opensearch_helper import add_connection_arguments, build_client
from utils.command import CustomBaseCommand

# The aliases the export command manages, used to scope the default `list` output.
KNOWN_ALIASES = sorted(set(TYPE_TO_INDEX.values()))


def _has_wildcard(name: str) -> bool:
    """Whether an index expression can match more than the single index it names."""
    return any(char in name for char in "*?") or "_all" in name.split(",")


def _is_managed(index: str, aliases: list[str]) -> bool:
    """Whether `index`, carrying `aliases`, belongs to an alias the export command manages.

    Besides the generations this also keeps two states an operator has to see: a concrete index
    named like an alias (which blocks the swap) and any index actually serving behind an alias.
    """
    return any(
        index == alias or alias in aliases or _is_generation_of(index, alias)
        for alias in KNOWN_ALIASES
    )


class Command(CustomBaseCommand):
    """Inspect and clean up the OpenSearch indices used by the OGC API Records search."""

    help = (
        "List, roll back, rename and delete the OpenSearch indices used by the OGC API Records "
        "search"
    )

    def add_arguments(self, parser: CommandParser) -> None:
        # Base class arguments (mainly '--logger').
        super().add_arguments(parser)

        # The connection flags are shared with the export command, so a run of either command
        # against the same cluster takes the same options.
        add_connection_arguments(parser)

        subparsers = parser.add_subparsers(dest="action", required=True)

        list_parser = subparsers.add_parser("list", help="List the indices and their aliases")
        list_parser.add_argument(
            "--all",
            action="store_true",
            help=(
                "List every index in the cluster, not only the aliases managed by "
                "oar_opensearch_export and their generations"
            ),
        )

        rollback_parser = subparsers.add_parser(
            "rollback", help="Point aliases back at an older generation, atomically"
        )
        rollback_parser.add_argument(
            "aliases",
            nargs="+",
            metavar="ALIAS",
            choices=KNOWN_ALIASES,
            help=f"Aliases to roll back, moved in one atomic request; one of {KNOWN_ALIASES}",
        )
        rollback_parser.add_argument(
            "--to",
            metavar="INDEX",
            help=(
                "Generation to point the alias at, instead of the one before the current one; "
                "only valid with a single alias"
            ),
        )
        rollback_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be rolled back without changing anything",
        )

        delete_parser = subparsers.add_parser("delete", help="Delete the given indices")
        delete_parser.add_argument(
            "indices",
            nargs="+",
            metavar="INDEX",
            help=(
                "Index names to delete; wildcards ('swissgeo-catalog-2026*') need --allow-wildcard"
            ),
        )
        delete_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without deleting anything",
        )
        delete_parser.add_argument(
            "--allow-wildcard",
            action="store_true",
            help="Acknowledge that the given patterns may match more than one index",
        )
        delete_parser.add_argument(
            "--force",
            action="store_true",
            help="Also delete indices still behind an alias, taking them out of the search results",
        )

        rename_parser = subparsers.add_parser(
            "rename", help="Rename an index, moving its aliases along with it"
        )
        rename_parser.add_argument(
            "source",
            metavar="SOURCE",
            help="Existing index name; wildcards are not accepted",
        )
        rename_parser.add_argument(
            "target",
            metavar="TARGET",
            help="New index name, which must not exist yet",
        )
        rename_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be renamed without changing anything",
        )
        rename_parser.add_argument(
            "--keep-source",
            action="store_true",
            help="Keep the source index after cloning instead of deleting it (copy, not rename)",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        client = build_client(self, options)

        if options["action"] == "list":
            self.list_indexes(client, show_all=options["all"])
        elif options["action"] == "rollback":
            self.rollback_aliases(
                client, options["aliases"], to=options["to"], dry_run=options["dry_run"]
            )
        elif options["action"] == "rename":
            self.rename_index(
                client,
                options["source"],
                options["target"],
                dry_run=options["dry_run"],
                keep_source=options["keep_source"],
            )
        else:
            self.delete_indexes(
                client,
                options["indices"],
                dry_run=options["dry_run"],
                allow_wildcard=options["allow_wildcard"],
                force=options["force"],
            )

    def resolve_indexes(self, client: Any, patterns: list[str]) -> dict[str, list[str]]:
        """Expand index names/wildcards into the existing indices and the aliases on each.

        `ignore_unavailable` keeps a pattern that matches nothing from raising, so a partly
        stale list of names still deletes the indices that do exist.
        """
        existing = client.indices.get(index=",".join(patterns), ignore_unavailable=True)
        return {index: sorted(existing[index].get("aliases", {})) for index in sorted(existing)}

    def list_indexes(self, client: Any, show_all: bool) -> None:
        """Print the indices with the aliases pointing at them, newest name last."""
        # Without --all, only ask for the managed aliases and their generations, so an unrelated
        # index in the same cluster stays out of the way.
        pattern = "*" if show_all else ",".join(f"{alias}*" for alias in KNOWN_ALIASES)
        indexes = client.indices.get(index=pattern, ignore_unavailable=True)
        # The prefix patterns also match indices that merely share the name of an alias, like
        # `swissgeo-catalog-backup`.
        if not show_all:
            indexes = {
                index: definition
                for index, definition in indexes.items()
                if _is_managed(index, list(definition.get("aliases", {})))
            }

        if not indexes:
            self.print_warning("No indices found.")
            return

        for index in sorted(indexes):
            # An index carries its aliases inline; a generation currently serving reads has the
            # alias attached, a superseded one has none.
            aliases = sorted(indexes[index].get("aliases", {}))
            suffix = f"  <- {', '.join(aliases)}" if aliases else ""
            self.print_success(f"{index}{suffix}")

        self.print_success(f"{len(indexes)} indices.")

    def rollback_aliases(
        self, client: Any, aliases: list[str], to: str | None, dry_run: bool
    ) -> None:
        """Point each alias at an older generation in a single atomic `_aliases` request.

        Every alias is validated before anything moves, and moving them together keeps the same
        guarantee as the export's swap: searches never see only some of the aliases switched.

        Rollback targets are not necessarily complete: a failed export leaves its generation
        behind, and it looks like any other one. Empty generations are refused and the document
        counts are reported, but check them -- with `--dry-run` first if in doubt.
        """
        aliases = list(dict.fromkeys(aliases))
        if to and len(aliases) > 1:
            raise CommandError("--to names one generation, so it takes a single alias")

        actions: list[dict] = []
        moves: list[str] = []
        for alias in aliases:
            if not _alias_exists(client, alias):
                raise CommandError(f"'{alias}' is not an alias pointing at any index")
            current = sorted(client.indices.get_alias(name=alias))
            target = self.rollback_target(client, alias, current, to)

            target_count = client.count(index=target)["count"]
            if not target_count:
                raise CommandError(
                    f"'{target}' is empty, most likely left behind by a failed export. "
                    f"Pick another generation of '{alias}' with --to"
                )
            current_count = client.count(index=alias)["count"]
            moves.append(
                f"Alias '{alias}': '{', '.join(current)}' ({current_count} documents) -> "
                f"'{target}' ({target_count} documents)"
            )

            actions += [{"remove": {"index": index, "alias": alias}} for index in current]
            actions.append({"add": {"index": target, "alias": alias}})

        if not dry_run:
            client.indices.update_aliases(body={"actions": actions})

        for move in moves:
            self.print_success(f"Would move {move}" if dry_run else f"Moved {move}")

    def rollback_target(self, client: Any, alias: str, current: list[str], to: str | None) -> str:
        """Pick the generation `alias` rolls back to: `to`, or the one before the current one."""
        existing = client.indices.get(index=f"{alias}-*", ignore_unavailable=True)
        generations = sorted(index for index in existing if _is_generation_of(index, alias))

        if to:
            # Only generations of this alias: an index of another record type would be accepted
            # by OpenSearch and silently serve the wrong documents.
            if to not in generations:
                raise CommandError(f"'{to}' is not an existing generation of '{alias}'")
            if to in current:
                raise CommandError(f"'{alias}' already points at '{to}'")
            return to

        if not _is_generation_of(current[-1], alias):
            raise CommandError(
                f"'{alias}' points at '{current[-1]}', which is not a generation, so there is no "
                "previous one. Pick a generation with --to"
            )
        # Timestamped names sort chronologically. Only older ones qualify: anything newer than
        # the current generation is a failed run or a generation already rolled back from.
        older = [index for index in generations if index < current[-1]]
        if not older:
            raise CommandError(f"'{alias}' has no generation older than '{current[-1]}'")
        return older[-1]

    def rename_index(
        self, client: Any, source: str, target: str, dry_run: bool, keep_source: bool
    ) -> None:
        """Rename `source` to `target`, carrying any aliases over.

        OpenSearch has no rename API, so this clones the index under the new name and deletes the
        original. A clone hard-links the underlying segments instead of copying documents, so it
        is cheap even for a large generation and reproduces the mappings and settings exactly --
        unlike a reindex, which rewrites every document. The tradeoff is that a clone cannot
        change the shard count, which a rename has no reason to do anyway.

        Cloning requires the source to reject writes, so the write block is set first and cleared
        again on the way out. With `keep_source` the source survives as a copy, and the block is
        lifted so it stays writable; otherwise it is deleted once the clone exists.
        """
        aliases = self.check_renameable(client, source, target)
        if dry_run:
            self.print_success(f"Would rename '{source}' to '{target}'")
            for alias in aliases:
                self.print_success(f"Would move alias '{alias}' to '{target}'")
            if keep_source:
                self.print_success(f"Would keep '{source}'")
            return

        # Block writes for the clone. Documents indexed between here and the clone would be lost,
        # which is exactly what the block prevents.
        self.print(f"Blocking writes on '{source}'")
        client.indices.put_settings(index=source, body={"index.blocks.write": True})
        try:
            self.print(f"Cloning '{source}' into '{target}'")
            client.indices.clone(index=source, target=target)
        except Exception:
            # The clone failed, so the source is staying: make it writable again rather than
            # leaving a read-only index behind.
            client.indices.put_settings(index=source, body={"index.blocks.write": None})
            raise

        # The clone inherits the write block from its source, so clear it on the new index.
        client.indices.put_settings(index=target, body={"index.blocks.write": None})

        if keep_source:
            client.indices.put_settings(index=source, body={"index.blocks.write": None})
        else:
            self.print(f"Deleting '{source}'")
            client.indices.delete(index=source)

        self.move_aliases(client, source, target, aliases, detach_source=keep_source)

        verb = "Copied" if keep_source else "Renamed"
        self.print_success(f"{verb} '{source}' to '{target}'.")

    def check_renameable(self, client: Any, source: str, target: str) -> list[str]:
        """Validate that `source` can be cloned to `target`, returning the aliases on `source`."""
        for name in (source, target):
            if _has_wildcard(name):
                raise CommandError(f"'{name}' is a wildcard; rename takes a single index name")

        existing = self.resolve_indexes(client, [source])
        if not existing:
            raise CommandError(f"No index matches {source}")
        # A non-wildcard name still resolves through an alias, which cannot be cloned.
        if source not in existing:
            raise CommandError(
                f"'{source}' is an alias for {', '.join(existing)}, not a concrete index"
            )
        if client.indices.exists(index=target):
            raise CommandError(f"'{target}' already exists")

        return existing[source]

    def move_aliases(
        self, client: Any, source: str, target: str, aliases: list[str], detach_source: bool
    ) -> None:
        """Point `aliases` at `target` in a single atomic `_aliases` request.

        Deleting the source drops its aliases with it, so they are simply re-added on the target.
        When the source is kept (`detach_source`), they have to be detached explicitly instead,
        otherwise the alias would resolve to both copies at once and double every search result.
        """
        if not aliases:
            return

        actions: list[dict] = []
        if detach_source:
            actions += [{"remove": {"index": source, "alias": alias}} for alias in aliases]
        actions += [{"add": {"index": target, "alias": alias}} for alias in aliases]

        client.indices.update_aliases(body={"actions": actions})
        for alias in aliases:
            self.print_success(f"Alias '{alias}' -> '{target}'")

    def delete_refusals(
        self, patterns: list[str], targets: dict[str, list[str]], allow_wildcard: bool, force: bool
    ) -> list[str]:
        """List why deleting `targets` has to be refused, given the acknowledgments passed."""
        refusals = []
        wildcards = [pattern for pattern in patterns if _has_wildcard(pattern)]
        if wildcards and not allow_wildcard:
            refusals.append(f"{', '.join(wildcards)} needs --allow-wildcard")
        # Deleting an index an alias still points at takes it out of the search results.
        if not force:
            refusals += [
                f"'{index}' is still behind alias {', '.join(aliases)} and serving reads; "
                "it needs --force"
                for index, aliases in targets.items()
                if aliases
            ]
        return refusals

    def delete_indexes(
        self, client: Any, patterns: list[str], dry_run: bool, allow_wildcard: bool, force: bool
    ) -> None:
        """Delete every index matching `patterns`, one request per index.

        The safety checks run before the first deletion, so a refused run deletes nothing.

        Deleting one at a time means a failure part-way through still leaves the already-deleted
        indices gone and reports which one broke, rather than failing opaquely for the whole set.
        """
        targets = self.resolve_indexes(client, patterns)
        if not targets:
            raise CommandError(f"No index matches {', '.join(patterns)}")

        refusals = self.delete_refusals(patterns, targets, allow_wildcard, force)

        if dry_run:
            for refusal in refusals:
                self.print_warning(f"Would refuse: {refusal}")
            for index in targets:
                self.print_success(f"Would delete '{index}'")
            self.print_success(f"{len(targets)} indices would be deleted (dry run).")
            return

        if refusals:
            raise CommandError(f"Nothing deleted: {'; '.join(refusals)}")

        for index, aliases in targets.items():
            if aliases:
                self.print_warning(f"'{index}' is behind alias {', '.join(aliases)}")
            self.print(f"Deleting '{index}'")
            client.indices.delete(index=index)

        self.print_success(f"Deleted {len(targets)} indices.")
