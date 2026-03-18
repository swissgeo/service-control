import json
from typing import TYPE_CHECKING, Any

import boto3
import environ

from dataservice.models import OGCAPIStacDataservice, WMSDataservice, WMTSDataservice
from dataset.models import Dataset
from distribution.models import (
    ExternalStacDistribution,
    ExternalWMSDistribution,
    ExternalWMTSDistribution,
)
from harvest.import_models import DatasetImport, LayersJSImport, OrganisationImport, ParsingError
from organization.models import Organization
from utils.command import CustomBaseCommand

if TYPE_CHECKING:
    from django.core.management.base import CommandParser

env = environ.Env()


class Command(CustomBaseCommand):
    """Import data from DynamoDB harvesting tables.

    This command imports data from DynamoDB harvesting tables. It currently supports importing
    organisations, but can be extended to import other entities in the future.

    """

    help = "Importing data from DynamoDB harvesting tables. "
    "Currently supports importing organisations."

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
            "--default-dataset",
            type=str,
            default="",
            help="Add distributions that cannot be automatically"
            " matched to a dataset to this dataset",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Main entry point of command."""

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options)}")

        # Ensure default dataset exists if required
        self.ensure_default_dataset()

        # Handle sub-commands
        if options["stac"]:
            self.sync_stac(*args, **options)

    # ##########################################################################
    def ensure_default_dataset(self) -> None:
        """Create the given default dataset if required and not yet available.

        This will create a provider and attribution with the same ID as the dataset.
        """

        if (
            not self.options["default_dataset"]
            or Dataset.objects.filter(dataset_id=self.options["default_dataset"]).first()
        ):
            return

        Dataset.objects.create(
            dataset_id=self.options["default_dataset"],
            title_short_de="#Missing",
            title_short_fr="#Missing",
            title_short_en="#Missing",
            description_de="#Missing",
            description_fr="#Missing",
            description_en="#Missing",
            geocat_id="#Missing",
        )
        self.print_success(f"Added default dataset '{self.options['default_dataset']}'")

    # ##########################################################################
    def sync_stac(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        """Sync from STAC capabilities."""

        for service in OGCAPIStacDataservice.objects.all():
            service.sync_from_capabilities(default_dataset_id=self.options["default_dataset"])
