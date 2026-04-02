import json
from typing import TYPE_CHECKING, Any

import boto3
import environ

from dataservice.models import WMSDataservice, WMTSDataservice
from dataset.models import Dataset
from distribution.models import (
    Distribution,
    ExternalGeoJSONDistribution,
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
            "--organisations",
            action="store_true",
            help="Import organisations",
        )
        parser.add_argument(
            "--datasets",
            action="store_true",
            help="Import datasets",
        )
        parser.add_argument(
            "--distributions",
            action="store_true",
            help="Import datasets",
        )

        parser.add_argument(
            "--target-env",
            type=str,
            choices=["dev", "int", "prod"],
            default="dev",
            help="Specify the target environment",
        )

        parser.add_argument(
            "--profile",
            type=str,
            nargs="?",
            default=None,
            help="Specify the profile name (only needed locally)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Main entry point of command."""
        profile = options.get("profile")
        if profile and profile != "default":
            self.session = boto3.Session(profile_name=profile)
        else:
            self.session = boto3.Session()

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options)}")

        # Handle sub-commands
        if options["organisations"]:
            self.import_organisations(*args, **options)
        if options["datasets"]:
            self.import_datasets(*args, **options)
        if options["distributions"]:
            self.import_distributions(*args, **options)

    # ##########################################################################
    def import_organisations(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        self.print_success("Importing organisations")

        dynamodb_client = self.session.client("dynamodb", region_name="eu-central-1")
        paginator = dynamodb_client.get_paginator("scan")

        for page in paginator.paginate(TableName=f"harvest-providers-{options['target_env']}"):
            for item in page["Items"]:
                try:
                    import_org = OrganisationImport.from_dynamodb_item(item)
                    self.print_success(
                        f"Parsed organisation: {import_org.provider_id} - {import_org.name_de}"
                    )
                except ParsingError as e:
                    self.print_error(f"Failed to parse item: {item}. Error: {e}")

                # check if we have an existing object with the same provider_id
                # if yes, get it from db and update values,
                # if not, create a new object
                try:
                    org = Organization.objects.get(organization_id=import_org.provider_id)
                except Organization.DoesNotExist:
                    self.print(
                        f"Organisation with provider_id {import_org.provider_id} does not exist yet"
                        ", creating a new one."
                    )
                    org = Organization(**import_org.model_dump(by_alias=True))
                else:
                    self.print(
                        f"Organisation with provider_id {import_org.provider_id} already exists, "
                        "updating."
                    )
                    for field in import_org:
                        setattr(org, field[0], field[1])

                org.save()

    # ##########################################################################
    def import_datasets(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        self.print_success("Importing datasets")

        dynamodb_client = self.session.client("dynamodb", region_name="eu-central-1")
        paginator = dynamodb_client.get_paginator("scan")

        for page in paginator.paginate(TableName=f"harvest-datasets-{options['target_env']}"):
            for item in page["Items"]:
                try:
                    import_ds = DatasetImport.from_dynamodb_item(item)
                    self.print_success(
                        f"Parsed dataset: {import_ds.dataset_id} - {import_ds.title_de}"
                    )
                except Exception as e:  # noqa: BLE001
                    self.print_error(f"Failed to parse item: {item}. Error: {e}")

                ds, _ = Dataset.objects.get_or_create(
                    dataset_id=import_ds.dataset_id,
                    defaults={
                        "title_short_de": import_ds.title_de,
                        "title_short_fr": import_ds.title_fr,
                        "title_short_en": import_ds.title_en,
                        "title_short_it": import_ds.title_it,
                        "title_short_rm": import_ds.title_rm,
                        "description_de": import_ds.description_de,
                        "description_fr": import_ds.description_fr,
                        "description_en": import_ds.description_en,
                        "description_it": import_ds.description_it,
                        "description_rm": import_ds.description_rm,
                        "geocat_id": import_ds.geocat_id,
                    },
                )

                ds.title_short_de = import_ds.title_de
                ds.title_short_fr = import_ds.title_fr
                ds.title_short_en = import_ds.title_en
                ds.title_short_it = import_ds.title_it
                ds.title_short_rm = import_ds.title_rm
                ds.description_de = import_ds.description_de
                ds.description_fr = import_ds.description_fr
                ds.description_en = import_ds.description_en
                ds.description_it = import_ds.description_it
                ds.description_rm = import_ds.description_rm
                ds.geocat_id = import_ds.geocat_id

                ds.save()

    # ##########################################################################
    def import_distributions(self, *args: Any, **options: Any) -> None:  # noqa: ARG002, C901

        self.print_success("Importing distributions")

        dynamodb_client = self.session.client("dynamodb", region_name="eu-central-1")
        paginator = dynamodb_client.get_paginator("scan")

        # Try to fetch the Geoadmin WMTS dataservice, which is needed to create WMTS distributions.
        try:
            wmts_dataservice = WMTSDataservice.objects.get(dataservice_id="wmts-geoadminch")
        except Dataset.DoesNotExist:
            self.print_error(
                "No Geoadmin WMTS Dataservice found, try to load fixtures first "
                "(./manage.py loaddata fixtures/dataservice.json"
            )
            return

        try:
            wms_dataservice = WMSDataservice.objects.get(dataservice_id="wms-geoadminch")
        except Dataset.DoesNotExist:
            self.print_error(
                "No Geoadmin WMTS Dataservice found, try to load fixtures first "
                "(./manage.py loaddata fixtures/dataservice.json"
            )
            return

        for page in paginator.paginate(TableName=f"harvest-layers-js-{options['target_env']}"):
            for item in page["Items"]:
                try:
                    ljs = LayersJSImport.from_dynamodb_item(item)
                    self.print_success(f"Parsed layers_js: {ljs.layer_id}")
                except Exception as e:  # noqa: BLE001
                    self.print_error(f"Failed to parse item: {item}. Error: {e}")

                try:
                    dataset = Dataset.objects.get(dataset_id=ljs.layer_id)
                except Dataset.DoesNotExist:
                    self.print_error(f"No Dataset found for layer_id {ljs.layer_id}")
                    continue

                # If the layertype is WMTS we create a WMTS and WMS distribution,
                # if it's WMS only a WMS distribution
                if ljs.layertype == "wmts":
                    dist = self.import_wmts_distribution(ljs, dataset, wmts_dataservice)
                    # Set the preferred distribution to WMTS for WMTS layers
                    dataset.preferred_distribution = dist
                    dataset.save()

                if ljs.layertype in ["wms", "wmts"]:
                    dist = self.import_wms_distribution(ljs, dataset, wms_dataservice)
                    # If the preferred distribution is not set yet, we set it to the WMS
                    # distribution
                    if not dataset.preferred_distribution:
                        dataset.preferred_distribution = dist
                        dataset.save()

                if ljs.layertype == "geojson":
                    dist = self.import_geojson_distribution(ljs, dataset)
                    # If the preferred distribution is not set yet,
                    # we set it to the GeoJSON distribution. Currently,
                    # layers of type geojson only have a GeoJSON distribution.
                    if not dataset.preferred_distribution:
                        dataset.preferred_distribution = dist
                        dataset.save()

    def import_wmts_distribution(
        self, ljs: LayersJSImport, dataset: Dataset, wmts_dataservice: WMTSDataservice
    ) -> Distribution:

        wmts_distribution_id = ljs.layer_id + ":wmts"
        self.print(f"Importing WMTS Distribution {wmts_distribution_id}")

        dist, _ = ExternalWMTSDistribution.objects.get_or_create(
            distribution_id=wmts_distribution_id,
            dataset=dataset,
            wmts_layer_name=ljs.layer_id,
        )
        dist.dataservice = wmts_dataservice
        dist.data_source = Distribution.DATA_SOURCE_CHOICE_BOD_LAYERS_JS
        dist.title = "WMTS Layer"

        # opacity must be between 0 (excluded) and 1 (included)
        if ljs.opacity and ljs.opacity <= 1 and ljs.opacity > 0:
            dist.opacity = ljs.opacity
        dist.save()
        return dist

    def import_wms_distribution(
        self, ljs: LayersJSImport, dataset: Dataset, wms_dataservice: WMSDataservice
    ) -> Distribution:

        wms_distribution_id = ljs.layer_id + ":wms"
        self.print(f"Importing WMS Distribution {wms_distribution_id}")

        dist, _ = ExternalWMSDistribution.objects.get_or_create(
            distribution_id=wms_distribution_id,
            dataset=dataset,
            wms_layer_name=ljs.layer_id,
        )
        dist.dataservice = wms_dataservice
        dist.data_source = Distribution.DATA_SOURCE_CHOICE_BOD_LAYERS_JS
        dist.title = "WMS Layer"

        # opacity must be between 0 (excluded) and 1 (included)
        if ljs.opacity and ljs.opacity <= 1 and ljs.opacity > 0:
            dist.opacity = ljs.opacity

        if ljs.wms_gutter:
            dist.gutter = ljs.wms_gutter
        dist.save()
        return dist

    def import_geojson_distribution(self, ljs: LayersJSImport, dataset: Dataset) -> Distribution:

        geojson_distribution_id = ljs.layer_id + ":geojson"
        self.print(f"Importing GeoJSON Distribution {geojson_distribution_id}")

        dist, _ = ExternalGeoJSONDistribution.objects.get_or_create(
            distribution_id=geojson_distribution_id,
            dataset=dataset,
            defaults={"geojson_url_de": ljs.geojson_url_de},
        )
        dist.data_source = Distribution.DATA_SOURCE_CHOICE_BOD_LAYERS_JS
        dist.title = "GeoJSON Layer"
        dist.geojson_url_de = ljs.geojson_url_de
        dist.geojson_url_fr = ljs.geojson_url_fr
        dist.geojson_url_it = ljs.geojson_url_it
        dist.geojson_url_en = ljs.geojson_url_en
        dist.geojson_url_rm = ljs.geojson_url_rm
        # The geojson style URL is not stored in the layers_js table,
        # but we can construct it from the layer_id
        # (see https://github.com/geoadmin/mf-chsdi3/blob/master/chsdi/models/bod.py#L142)
        # Note: we always reference prod env here
        dist.style_url = "https://api3.geo.admin.ch/static/vectorStyles/" + ljs.layer_id + ".json"
        dist.save()
        return dist
