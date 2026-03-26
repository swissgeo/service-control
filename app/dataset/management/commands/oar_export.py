import json
from typing import TYPE_CHECKING, Any

import boto3
import environ
from botocore.client import Config

from dataservice.models import Dataservice
from dataset.export_models import LANGS, OAFeatureCollection, OARDataservice, OARDistribution
from dataset.models import Dataset
from utils.command import CustomBaseCommand

if TYPE_CHECKING:
    from django.core.management.base import CommandParser


env = environ.Env()

OAR_PREFIX = "api/oar/v0"
OAS_PREFIX = "api/oas/v0"
ENV_HOSTNAME_POSTFIX = "dev.sgdi.tech"
OAR_BASE_URL = f"https://services.{ENV_HOSTNAME_POSTFIX}/{OAR_PREFIX}"
OAS_BASE_URL = f"https://services.{ENV_HOSTNAME_POSTFIX}/{OAS_PREFIX}"

SAMPLE_IDS = [
    "ch.bafu.schutzgebiete-luftfahrt",
    "ch.swisstopo.lubis-luftbilder-dritte-kantone",
    "ch.bav.sachplan-infrastruktur-schiene_anhorung",
    "ch.agroscope.korridore-feuchtgebietsarten_qualitaet",
    "ch.meteoschweiz.messwerte-pollen-buche-1h",
]


# For some reason geocat uses a legacy 3-letter bibliographic code
# that we need to map to ISO 639-1 codes
LANGS_GEOCAT = {
    "de": "ger",
    "fr": "fra",
    "it": "ita",
    "en": "eng",
}


class Command(CustomBaseCommand):
    """Manage OGC API Records Content.

    Currently, this command harvests various sources, merges their content,
    and writes static OGC API Records compliant JSON files to S3

    Note:
        There are a number of fields/information missing that will be added in later iterations:
            - related description link

    """

    help = "OAR management"

    def add_arguments(self, parser: CommandParser) -> None:
        # Call the base class method to get default arguments defined in the base class
        # (mainly 'logger')
        super().add_arguments(parser)

        # Sub-commands
        sub = parser.add_subparsers(dest="command", required=False, help="Sub-commands")

        parser.add_argument(
            "--dump",
            action="store_true",
            help="Dump the generated records (for debugging)",
        )
        parser.add_argument(
            "--upload",
            action="store_true",
            help="Upload the generated records to S3",
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
            default="default",
            help="AWS CLI profile to use for authentication (default: 'default')",
        )
        parser.add_argument(
            "--types",
            type=str,
            nargs="+",
            choices=["services", "distributions", "landing_page"],
            help="Select the type of records to export",
        )

        clean = sub.add_parser("clean", help="Delete static files from S3 buckets")
        clean.add_argument(
            "--batch-size", type=int, default=1000, help="Number of files to delete per batch"
        )
        clean.add_argument(
            "--records",
            action="store_true",
            help="Delete exported OARecords files from the S3 bucket",
        )
        clean.add_argument(
            "--styles",
            action="store_true",
            help="Delete exported OARecords styles from the S3 bucket",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Main entry point of command."""
        if options["profile"]:
            self.session = boto3.Session(profile_name=options["profile"])  # pylint: disable=attribute-defined-outside-init
        else:
            self.session = boto3.Session()  # pylint: disable=attribute-defined-outside-init

        # S3 client configuration
        client_access_kwargs = {
            "region_name": "eu-central-1",
            "config": Config(signature_version="s3v4"),
        }
        self.s3_client = self.session.client("s3", **client_access_kwargs)  # ty:ignore[no-matching-overload]

        # derive bucket names from target environment
        self.oarecords_s3_bucket = f"oa-records-static-{options['target_env']}-swissgeo"
        self.oastyles_s3_bucket = f"oa-styles-static-{options['target_env']}-swissgeo"

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options)}")

        if "services" in options["types"]:
            self.do_export_services(*args, **options)
        elif "distributions" in options["types"]:
            self.do_export_distributions(*args, **options)

        if options["command"] == "clean":
            self.do_clean(*args, **options)

    # ##########################################################################
    def do_upload(self, snippets: dict[str, Any], prefix: str = OAR_PREFIX) -> None:
        """Helper function to upload a dict of OGC API Records snippets to S3.

        Args:
            snippets: A dict where the key is the relative path (after the base URL,
                      e.g. "/collections/{collection_id}/items/{item_id}.{lang}")
                      and the value is the JSON content to upload.
            prefix: The prefix to use for the S3 object keys (default: OAR_PREFIX)
        """
        for key, snippet in snippets.items():
            self.s3_client.put_object(
                Bucket=self.oarecords_s3_bucket,
                Key=f"{prefix}{key}",
                Body=json.dumps(snippet, indent=2, ensure_ascii=False).encode("utf-8"),
                ContentType="application/json",
            )
            self.print(f" - {prefix}{key}")

    # ##########################################################################
    def do_export_services(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        services = {}

        # Write service files
        # Note: these snippets are not localised (yet), but we still need to upload
        # 4 lang versions to please the CF function language hack
        self.print("Generating service records...")
        for service in Dataservice.objects.all():
            for lang in LANGS:
                self.print(f" - {service.dataservice_id}")
                service_record = OARDataservice.from_dataservice(service)
                services[
                    f"/collections/geoadmin.services/items/{service.dataservice_id}.{lang}"
                ] = service_record.model_dump(exclude_none=True, by_alias=True)

        if options["dump"]:
            self.print(json.dumps(services, indent=2, ensure_ascii=False))

        if options["upload"]:
            self.print_success("Starting to upload local OGC API Records to S3...")
            self.do_upload(services, prefix=OAR_PREFIX)

    # ##########################################################################
    def do_export_distributions(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        distribution_collections = {}
        distributions = {}

        # Aggregate distribution collection and distribution snippets
        # Note: these snippets are not localised (yet), but we still need to upload
        # 4 lang versions to please the CF function language hack
        self.print("Generating distribution records...")
        for dataset in Dataset.objects.all():
            ds_distributions = list(dataset.distribution_set.all())  # ty:ignore[unresolved-attribute]
            for lang in LANGS:
                distribution_collection = OAFeatureCollection()
                for distribution in ds_distributions:
                    self.print(f" - {distribution.distribution_id}.{lang}")
                    distribution_record = OARDistribution.from_distribution(distribution, lang=lang)
                    distribution_collection.features.append(distribution_record)
                    distributions[
                        f"/collections/{dataset.dataset_id}/items/{distribution.distribution_id}.{lang}"
                    ] = distribution_record.model_dump(
                        exclude_none=True,
                        by_alias=True,
                    )
                distribution_collections[f"/collections/{dataset.dataset_id}/items.{lang}"] = (
                    distribution_collection.model_dump(exclude_none=True, by_alias=True)
                )

        # Dump the generated records (for debugging)
        if options["dump"]:
            self.print(json.dumps(distribution_collections, indent=2, ensure_ascii=False))

        # Upload the generated records to S3
        if options["upload"]:
            self.print_success("Starting to upload local OGC API Records to S3...")
            self.do_upload(distribution_collections, prefix=OAR_PREFIX)
            self.do_upload(distributions, prefix=OAR_PREFIX)

    # ##########################################################################
    def do_export_landing_page(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        # Landing page
        self.print("Uploading landing page...")
        landing_page = {
            "title": "OGC API Records - swissgeo",
            "description": "OGC API Records implementation for swissgeo datasets and services.",
            "links": [
                {
                    "href": f"{OAR_BASE_URL}/collections/swissgeo.catalog",
                    "rel": "service-desc",
                    "type": "application/json",
                    "title": "OGC API Records - swissgeo - OpenAPI Description",
                },
                {
                    "href": f"{OAR_BASE_URL}/collections",
                    "rel": "data",
                    "type": "application/json",
                    "title": "Swissgeo Catalog Collection",
                },
                {
                    "href": f"{OAR_BASE_URL}/conformance",
                    "rel": "conformance",
                    "type": "application/json",
                    "title": "Conformance Declaration",
                },
            ],
        }
        self.s3_client.put_object(
            Bucket=self.oarecords_s3_bucket,
            Key=f"{OAR_PREFIX}/landingpage",
            Body=json.dumps(landing_page, indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )

        # conformance declaration
        self.print("Uploading conformance declaration...")
        conformance_declaration = {
            "conformsTo": [
                "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core",
                "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/collections",
                "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/json",
            ]
        }
        for lang in LANGS:
            self.s3_client.put_object(
                Bucket=self.oarecords_s3_bucket,
                Key=f"{OAR_PREFIX}/conformance.{lang}",
                Body=json.dumps(conformance_declaration, indent=2, ensure_ascii=False).encode(
                    "utf-8"
                ),
                ContentType="application/json",
            )

        # /collections endpoint
        self.print("Uploading collections endpoint...")
        collections = {
            "collections": [
                {
                    "id": "swissgeo.catalog",
                    "title": "Swissgeo Catalog",
                    "description": "Collection of all swissgeo datasets",
                    "itemType": "record",
                    "links": [
                        {
                            "href": f"{OAR_BASE_URL}/collections/swissgeo.catalog",
                            "rel": "self",
                            "type": "application/json",
                        },
                        {
                            "href": f"{OAR_BASE_URL}/collections/swissgeo.catalog/items",
                            "rel": "items",
                            "type": "application/json",
                        },
                    ],
                },
                {
                    "id": "geoadmin.services",
                    "title": "Geoadmin Services",
                    "description": "Collection of geoadmin services",
                    "itemType": "record",
                    "links": [
                        {
                            "href": f"{OAR_BASE_URL}/collections/geoadmin.services",
                            "rel": "self",
                            "type": "application/json",
                        }
                    ],
                },
            ],
            "links": [
                {
                    "href": f"{OAR_BASE_URL}/collections",
                    "rel": "self",
                    "description": "This document",
                    "type": "application/json",
                }
            ],
        }
        for lang in LANGS:
            self.s3_client.put_object(
                Bucket=self.oarecords_s3_bucket,
                Key=f"{OAR_PREFIX}/collections.{lang}",
                Body=json.dumps(collections, indent=2, ensure_ascii=False).encode("utf-8"),
                ContentType="application/json",
            )

        self.print_success("Export completed.")
        # endregion

    # ##########################################################################
    def do_clean(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        buckets = []
        if options["records"]:
            buckets.append(self.oarecords_s3_bucket)
        if options["styles"]:
            buckets.append(self.oastyles_s3_bucket)

        for bucket in buckets:
            self.print_success(
                f"Cleaning bucket: {bucket}. "
                "(delete files in batches of {options['batch_size']} files)..."
            )

            nr_objs = 0

            kwargs = {"Bucket": bucket, "MaxKeys": options["batch_size"]}
            result = self.s3_client.list_objects_v2(**kwargs)
            objs = result.get("Contents", [])
            while objs:
                nr_objs += len(objs)
                self.print(f"Found {len(objs)} more objects to delete in {bucket}...")
                keys = [{"Key": obj["Key"]} for obj in objs]
                self.print(f"Deleting {len(keys)} objects from {bucket}...")
                for key in keys:
                    self.print(f" - {key['Key']}")
                self.s3_client.delete_objects(Bucket=bucket, Delete={"Objects": keys})
                if "NextContinuationToken" in result:
                    result = self.s3_client.list_objects_v2(
                        ContinuationToken=result.get("NextContinuationToken"), **kwargs
                    )
                    objs = result.get("Contents", [])
                else:
                    break
            self.print_success(f"Deleted total of {nr_objs} objects from {bucket}.")
