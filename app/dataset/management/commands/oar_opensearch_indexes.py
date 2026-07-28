"""List and delete the OpenSearch indices backing the OGC API Records search.

This is an operational companion to `oar_opensearch_export`: that command creates timestamped
generations and swaps the aliases over, this one lets you inspect what is currently in the
cluster and remove indices that are no longer wanted.

    manage.py oar_opensearch_indexes list
    manage.py oar_opensearch_indexes list --all
    manage.py oar_opensearch_indexes delete swissgeo-catalog-20260722100000
    manage.py oar_opensearch_indexes delete 'swissgeo-catalog-2026*' --dry-run

Deletion is unrestricted: whatever index names or patterns you pass are deleted, without a
confirmation prompt. A wildcard that matches more than you expect will delete more than you
expect -- use `--dry-run` first.
"""

from typing import Any

from django.core.management.base import CommandError, CommandParser

from dataset.management.commands.oar_opensearch_export import TYPE_TO_INDEX
from dataset.opensearch_helper import add_connection_arguments, build_client
from utils.command import CustomBaseCommand

# The aliases the export command manages, used to scope the default `list` output.
KNOWN_ALIASES = sorted(set(TYPE_TO_INDEX.values()))


class Command(CustomBaseCommand):
    """Inspect and clean up the OpenSearch indices used by the OGC API Records search."""

    help = "List and delete the OpenSearch indices used by the OGC API Records search"

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

        delete_parser = subparsers.add_parser("delete", help="Delete the given indices")
        delete_parser.add_argument(
            "indices",
            nargs="+",
            metavar="INDEX",
            help="Index names to delete; wildcards ('swissgeo-catalog-2026*') are supported",
        )
        delete_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without deleting anything",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        client = build_client(self, options)

        if options["action"] == "list":
            self.list_indexes(client, show_all=options["all"])
        else:
            self.delete_indexes(client, options["indices"], dry_run=options["dry_run"])

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

    def delete_indexes(self, client: Any, patterns: list[str], dry_run: bool) -> None:
        """Delete every index matching `patterns`, one request per index.

        Deleting one at a time means a failure part-way through still leaves the already-deleted
        indices gone and reports which one broke, rather than failing opaquely for the whole set.
        """
        targets = self.resolve_indexes(client, patterns)
        if not targets:
            raise CommandError(f"No index matches {', '.join(patterns)}")

        # Deleting an index an alias still points at takes it out of the search results, so it is
        # worth calling out even though it does not stop the deletion.
        for index, aliases in targets.items():
            if aliases:
                self.print_warning(
                    f"'{index}' is still behind alias {', '.join(aliases)} and serving reads"
                )

        if dry_run:
            for index in targets:
                self.print_success(f"Would delete '{index}'")
            self.print_success(f"{len(targets)} indices would be deleted (dry run).")
            return

        for index in targets:
            self.print(f"Deleting '{index}'")
            client.indices.delete(index=index)

        self.print_success(f"Deleted {len(targets)} indices.")
