import json
from typing import Any

import environ
from pystac_client import Client

from django.core.management.base import CommandParser

from dataservice.models import OGCAPIStacDataservice
from dataset.models import Dataset
from distribution.models import Distribution, ExternalStacDistribution
from harvest.models import DatasetMapping
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
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Clean up",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Main entry point of command."""

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options, default=str)}")

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

        self.print_success("Sync from STAC")

        metrics = {
            "collections.processed": 0,
            "distributions.added": 0,
            "distributions.updated": 0,
            "distributions.obsolete": 0,
            "distributions.removed": 0,
        }
        success = True
        for service in OGCAPIStacDataservice.objects.all():
            self.print(f"Syncing dataservice '{service.dataservice_id}' from capabilities...")
            try:
                processed, added, updated, obsolete = self.sync_stac_from_capabilities(
                    service,
                )
                metrics["collections.processed"] += processed
                metrics["distributions.added"] += added
                metrics["distributions.updated"] += updated
                metrics["distributions.obsolete"] += obsolete if not self.options["clean"] else 0
                metrics["distributions.removed"] += obsolete if self.options["clean"] else 0
                self.print_success(
                    f"Finished syncing dataservice '{service.dataservice_id}' from capabilities."
                )
            except Exception as e:  # noqa: BLE001
                success = False
                self.print_error(
                    f"Error syncing dataservice '{service.dataservice_id}' from capabilities: {e}"
                )

        self.write_command_metrics(metrics)
        if success:
            self.print_success(f"Sync from STAC completed. Metrics: {metrics}")
        else:
            self.print_warning(f"Sync from STAC completed with errors. Metrics: {metrics}")

    def sync_stac_from_capabilities(  # noqa:C901,PLR0912,PLR0915
        self, dataservice: OGCAPIStacDataservice
    ) -> tuple[int, int, int, int]:
        """Evaluate the capabilities to detect distributions.

        We try to map STAC collection_ids automatically to datasets. If no matching
        dataset is found, the distribution is added to the default dataset (if given).

        Returns the number of STAC collections, number of added distributions, number of updated
        distributions and the number of obsolete/removed distributions.
        """

        mappings = DatasetMapping.table()

        processed = set()
        added = 0
        updated = 0

        try:
            orphanage_dataset = Dataset.objects.get(dataset_id=self.options["orphanage_dataset"])
        except Dataset.DoesNotExist:
            self.print_error(
                "Default dataset with ID %s not found. Please create this dataset before "
                "running the sync or provide a different default dataset ID.",
                self.options["orphanage_dataset"],
            )
            raise

        # Get managed collections from STAC API
        client = Client.open(dataservice.landing_page_url)
        for collection in client.collection_search().collections():
            collection_id = collection.id
            processed.add(collection_id)
            self.print(f"Processing collection {collection_id}")

            dataset, mapping = mappings.match(collection_id)
            if mapping and not mapping.enabled_for_stac_distribution:
                dataset = None
            if dataset:
                self.print(f"Mapping found for collection_id {collection_id}: {dataset}")

            # check if distribution with this collection_id already exists
            try:
                distribution = ExternalStacDistribution.objects.get(
                    stac_collection_id=collection_id,
                    dataservice=dataservice,
                )
                self.print(
                    "Distribution for collection_id %s already exists, "
                    "skipping creation for dataservice %s.",
                    collection_id,
                    dataservice.dataservice_id,
                )
            except ExternalStacDistribution.DoesNotExist:
                if not dataset:
                    # try to find a dataset with the same dataset_id as the collection_id
                    dataset = Dataset.objects.filter(dataset_id=collection_id).first()

                if not dataset:
                    self.print_warning(
                        "No dataset found for collection_id %s, "
                        "adding distribution to orphanage dataset %s.",
                        collection_id,
                        self.options["orphanage_dataset"],
                    )
                    dataset = orphanage_dataset

                # create new distribution
                ExternalStacDistribution.objects.create(
                    distribution_id=f"{collection_id}:stac",
                    dataset=dataset,
                    title="STAC Download Collection",
                    data_source=Distribution.DataSource.SERVICE_CAPABILITIES,
                    dataservice=dataservice,
                    stac_collection_id=collection_id,
                )
                added += 1
                self.print(
                    f"Added distribution for collection_id {collection_id} to "
                    f"dataset {dataset.dataset_id} from dataservice {dataservice.dataservice_id}."
                )
            else:
                # Use the dataset from the mapping if available
                if dataset and mapping and mapping.update and distribution.dataset != dataset:
                    distribution.dataset = dataset
                    distribution.save()
                    updated += 1
                    self.print(
                        f"Updated distribution for collection_id {collection_id} to "
                        f"dataset {dataset.dataset_id} from "
                        f"dataservice {dataservice.dataservice_id}."
                    )

                # If the distribution is linked to the orphanage dataset, we check if there's
                # a dataset now matching the collection_id and link it to this dataset if found
                if distribution.dataset == orphanage_dataset:
                    dataset = Dataset.objects.filter(dataset_id=collection_id).first()
                    if dataset:
                        distribution.dataset = dataset
                        distribution.save()
                        updated += 1
                        self.print(
                            f"Updated distribution for collection_id {collection_id} to "
                            f"dataset {dataset.dataset_id} from "
                            f"dataservice {dataservice.dataservice_id}."
                        )

        obsolete = (
            ExternalStacDistribution.objects.filter(
                data_source=Distribution.DataSource.SERVICE_CAPABILITIES
            )
            .exclude(stac_collection_id__in=processed)
            .all()
        )
        if obsolete:
            if self.options["clean"]:
                for distribution in obsolete:
                    self.print_warning(f"Removing obsolete distribution {distribution}")
                    distribution.delete()
            else:
                self.print_warning(
                    f"Obsolete distribution found: {', '.join(str(d) for d in obsolete)}"
                )

        return len(processed), added, updated, len(obsolete)
