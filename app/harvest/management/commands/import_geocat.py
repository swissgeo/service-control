import json
from http import HTTPStatus
from typing import Any

from lxml import etree  # ty:ignore[unresolved-import]
from requests import get

from django.core.management.base import CommandParser

from dataset.models import Dataset
from thesaurus.models import ECH0166_THESAURUS_ID, Concept, Thesaurus
from utils.command import CustomBaseCommand

GEOCAT_URL = "https://www.geocat.ch/geonetwork/srv/api/records/{}/formatters/xml?approved=true"
NS = {"che": "http://geocat.ch/che", "mri": "http://standards.iso.org/iso/19115/-3/mri/1.0"}


class Command(CustomBaseCommand):
    """Harvest data from geocat."""

    help = "Import geocat metadata."

    def add_arguments(self, parser: CommandParser) -> None:
        # Call the base class method to get default arguments defined in the base class
        # (mainly 'logger')
        super().add_arguments(parser)

        # Select parts to import
        parser.add_argument(
            "--ech0166",
            action="store_true",
            help="Import eCH-0166 categories",
        )

        # Other options
        parser.add_argument(
            "--timeout",
            type=int,
            default="30",
            help="Timeout when calling geocat",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        """Main entry point of command."""

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options, default=str)}")

        # Check if required fixtures are loaded
        if options["ech0166"] and not Thesaurus.objects.filter(thesaurus_id=ECH0166_THESAURUS_ID):
            self.print_error(
                "No eCH-0166 thesaurus not found, try to load the fixture first "
                "(./manage.py loaddata fixtures/ech0166.json)"
            )
            return

        # Check if anything is selected
        if not options["ech0166"]:
            self.print_error("Select at least one option")
            return

        metrics = {"datasets.updated": 0}

        # Harvest geocat information based on known datasets
        for dataset in Dataset.objects.iterator():
            if not dataset.geocat_id:
                self.print(f"Skipping {dataset} as it has no geocat_id")
                continue

            response = get(GEOCAT_URL.format(dataset.geocat_id), timeout=options["timeout"])
            if response.status_code != HTTPStatus.OK:
                self.print_warning(
                    f"Dataset {dataset} has no valid geocat entry "
                    f"(id: '{dataset.geocat_id}', status code: {response.status_code})"
                )
                continue

            try:
                root = etree.fromstring(response.content)
            except etree.LxmlError:
                self.print_warning(f"Dataset {dataset} has no valid geocat XML")
                continue

            # Handle sub-commands
            if options.get("ech0166"):
                metrics["datasets.updated"] += self.import_ech0166(dataset, root)

        self.print_success(f"Geocat import completed. Metrics: {metrics}")

    def import_ech0166(
        self,
        dataset: Dataset,
        root: etree._Element,
    ) -> int:
        """Get all eCH-0166 categories.

        Queries all eCH-0166 categories for the given dataset from geocat and stores them on the
        dataset (i.e. links the corresponding concepts). Requires to have the thesaurus loaded first
        (via ./manage.py loaddata fixtures/ech0166.json). Removes obsolete concepts.

        Returns the number of updated datasets.
        """

        self.print(f"Getting eCH-0166 categories for dataset {dataset}")

        # Collect existing eCH-0166 concepts of the dataset
        existing = dataset.concepts.filter(thesaurus__thesaurus_id=ECH0166_THESAURUS_ID).all()
        existing_ids = {concept.concept_id for concept in existing}

        # Collect concepts from geocat
        concept_ids = {e.text for e in root.findall(".//mri:MD_TopicCategoryCode", NS)} | {
            e.attrib["codeListValue"]
            for e in root.findall(".//che:CHE_MD_SubTopicCategoryCode", NS)
        }

        updated = False

        # Add new ones
        for concept_id in concept_ids - existing_ids:
            updated = True
            concept = Concept.objects.filter(
                thesaurus__thesaurus_id=ECH0166_THESAURUS_ID, concept_id=concept_id
            ).first()
            if not concept:
                self.print_warning(f"Unknown concept {concept_id}")
                continue

            self.print(f"Adding {concept} to {dataset}")
            dataset.concepts.add(concept)

        # Remove obsolete ones
        obsolete = [concept for concept in existing if concept.concept_id not in concept_ids]
        for concept in obsolete:
            updated = True
            self.print(f"Removing {concept} from {dataset}")
            dataset.concepts.remove(concept)

        return 1 if updated else 0
