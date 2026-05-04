import json
from typing import Any

import environ

from django.core.management.base import CommandParser

from dataservice.models import OGCAPIStacDataservice
from dataset.models import Dataset
from utils.command import CustomBaseCommand

env = environ.Env()


class Command(CustomBaseCommand):
    """Import data from Service Capabilities..

    This command tries to infer/sync distributions from STAC and other capability files.

    """

    help = "This command tries to infer/sync distributions from STAC and other capability files."

    def add_arguments(self, parser: CommandParser) -> None:
        # Call the base class method to get default arguments defined in the base class
        # (mainly 'logger')
        super().add_arguments(parser)

        # Select entities to import
        parser.add_argument(
            "--stac",
            action="store_true",
            help="Sync from STAC capabilities (imports datasets and distributions)",
        )
        parser.add_argument(
            "--orphanage-dataset",
            type=str,
            default="ORPHANAGE",
            help="Add distributions that cannot be automatically"
            " matched to a dataset to this dataset",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Main entry point of command."""

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options)}")

        # Ensure default dataset exists if required
        self.ensure_orphanage_dataset()

        # Handle sub-commands
        if options["stac"]:
            self.sync_stac(*args, **options)

    # ##########################################################################
    def ensure_orphanage_dataset(self) -> None:
        """Create the given default dataset if required and not yet available.

        This will create a provider and attribution with the same ID as the dataset.
        """

        if (
            not self.options["orphanage_dataset"]
            or Dataset.objects.filter(dataset_id=self.options["orphanage_dataset"]).first()
        ):
            return

        Dataset.objects.create(
            dataset_id=self.options["orphanage_dataset"],
            title_short_de="#Missing",
            title_short_fr="#Missing",
            title_short_en="#Missing",
            description_de="#Missing",
            description_fr="#Missing",
            description_en="#Missing",
            geocat_id="#Missing",
        )
        self.print_success(f"Added orphanage dataset '{self.options['orphanage_dataset']}'")

    # ##########################################################################
    def sync_stac(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        """Sync from STAC capabilities."""

        for service in OGCAPIStacDataservice.objects.all():
            self.print(f"Syncing dataservice '{service.dataservice_id}' from capabilities...")
            try:
                service.sync_from_capabilities(
                    orphanage_dataset_id=self.options["orphanage_dataset"]
                )
                self.print_success(
                    f"Finished syncing dataservice '{service.dataservice_id}' from capabilities."
                )
            except Exception as e:  # noqa: BLE001
                self.print_error(
                    f"Error syncing dataservice '{service.dataservice_id}' from capabilities: {e}"
                )
