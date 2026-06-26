import json
from typing import Any

import environ
from boto3 import Session
from botocore.client import Config

from django.core.management.base import CommandParser

from dataservice.models import Dataservice
from dataset.export_models import (
    LANGS,
    OARCollection,
    OARDataservice,
    OARDataset,
    OARDistribution,
)
from dataset.models import Dataset
from utils.command import CustomBaseCommand

env = environ.Env()

OAR_PREFIX = "api/oar/staticv2"
OAS_PREFIX = "api/oas/v0"
OAR_BASE_URL = {
    "dev": f"https://services.dev.sgdi.tech/{OAR_PREFIX}",
    "int": f"https://services.int.sgdi.tech/{OAR_PREFIX}",
    "prod": f"https://services.swissgeo.ch/{OAR_PREFIX}",
    "local": f"http://localhost:5001/oa-records-static-v2-local-swissgeo/{OAR_PREFIX}",
}
OAS_BASE_URL = {
    "dev": f"https://services.dev.sgdi.tech/{OAS_PREFIX}",
    "int": f"https://services.int.sgdi.tech/{OAS_PREFIX}",
    "prod": f"https://services.swissgeo.ch/{OAS_PREFIX}",
    "local": f"http://localhost:5001/oa-styles-static-local-swissgeo/{OAS_PREFIX}",
}

SAMPLE_IDS = [
    "ch.bafu.schutzgebiete-luftfahrt",
    "ch.swisstopo.lubis-luftbilder-dritte-kantone",
    "ch.bav.sachplan-infrastruktur-schiene_anhorung",
    "ch.agroscope.korridore-feuchtgebietsarten_qualitaet",
    "ch.meteoschweiz.messwerte-pollen-buche-1h",
]


class Command(CustomBaseCommand):
    """Export data entities to OGC API Records service.

    Currently this command derives OAR records conform snippets
    from the local database and uploads them to S3.
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
            choices=["dev", "int", "prod", "local"],
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
            "--sample",
            action="store_true",
            help="Only process a sample of datasets and distributions (for testing)",
        )
        parser.add_argument(
            "--types",
            type=str,
            nargs="+",
            default=[],
            choices=["services", "distributions", "datasets", "landing_page"],
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
        profile = options.get("profile")
        if profile and profile != "default":
            self.session = Session(profile_name=profile)
        else:
            self.session = Session()

        # S3 client configuration
        client_access_kwargs = {
            "region_name": "eu-central-1",
            "config": Config(signature_version="s3v4"),
        }
        target_env = options["target_env"]
        if target_env == "local":
            client_access_kwargs["region_name"] = env.str("AWS_DEFAULT_REGION")
            client_access_kwargs["endpoint_url"] = "http://localhost:5000"
        self.s3_client = self.session.client("s3", **client_access_kwargs)  # ty:ignore[no-matching-overload]

        # derive bucket names from target environment
        self.oarecords_s3_bucket = f"oa-records-static-v2-{target_env}-swissgeo"
        self.oastyles_s3_bucket = f"oa-styles-static-{target_env}-swissgeo"

        # urls
        self.oar_base_url = OAR_BASE_URL[target_env]
        self.oas_base_url = OAS_BASE_URL[target_env]

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options, default=str)}")

        if "services" in options["types"]:
            self.do_export_services(*args, **options)
        if "distributions" in options["types"]:
            self.do_export_distributions(*args, **options)
        if "datasets" in options["types"]:
            self.do_export_datasets(*args, **options)
        if "landing_page" in options["types"]:
            self.do_export_landing_page(*args, **options)

        if options["command"] == "clean":
            self.do_clean(*args, **options)

    def upload_object(self, key: str, obj: dict) -> None:
        """Helper function to upload a single OGC API Record object to S3."""
        self.s3_client.put_object(
            Bucket=self.oarecords_s3_bucket,
            Key=f"{key}",
            Body=json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
        self.print_success(f" ↑ {key}")

    def upload_collection(self, collection: OARCollection, prefix: str = OAR_PREFIX) -> None:
        """Helper function to upload an OARCollection
        (including its feature collection and features) to S3."""
        # Upload the collection itself
        self.upload_object(
            key=f"{prefix}{collection.get_key()}",
            obj=collection.model_dump(exclude_none=True, by_alias=True),
        )

        # Upload the feature collection
        self.upload_object(
            key=f"{prefix}{collection.feature_collection.get_key()}",
            obj=collection.feature_collection.model_dump(exclude_none=True, by_alias=True),
        )

        # Upload each feature in the collection
        for feature in collection.feature_collection.features:
            self.upload_object(
                key=f"{prefix}{feature.get_key()}",
                obj=feature.model_dump(exclude_none=True, by_alias=True),
            )

    def dump_collection(self, collection: OARCollection) -> None:
        """Helper function to dump an OARCollection
        (including its feature collection and features) to the console."""
        self.print(collection.get_key())
        self.print(
            json.dumps(
                collection.model_dump(exclude_none=True, by_alias=True),
                indent=2,
                ensure_ascii=False,
            )
        )
        self.print(collection.feature_collection.get_key())
        self.print(
            json.dumps(
                collection.feature_collection.model_dump(exclude_none=True, by_alias=True),
                indent=2,
                ensure_ascii=False,
            )
        )
        # Probably too verbose to dump each feature in the collection,
        # but can be uncommented for debugging
        # for feature in collection.feature_collection.features:
        #     self.print(feature.get_key())
        #     self.print(
        #         json.dumps(
        #             feature.model_dump(exclude_none=True, by_alias=True),
        #             indent=2,
        #             ensure_ascii=False,
        #         )
        #     )

    def do_export_services(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        services = {}

        # Write service files
        # Note: these snippets are not localised (yet), but we still need to upload
        # 4 lang versions to please the CF function language hack
        self.print("Generating service records...")
        services = Dataservice.objects.all()
        for lang in LANGS:
            collection_id = "geoadmin.services"
            service_collection = OARCollection(
                id=collection_id, title="Geoadmin Services", lang=lang, base_url=self.oar_base_url
            )
            for service in services:
                self.print(f" - {service.dataservice_id}")
                service_record = OARDataservice.from_dataservice(
                    service, lang, collection_id=collection_id, base_url=self.oar_base_url
                )
                service_collection.feature_collection.features.append(service_record)

            if options["dump"]:
                self.dump_collection(service_collection)

            if options["upload"]:
                self.upload_collection(
                    service_collection,
                    prefix=OAR_PREFIX,
                )

    def do_export_distributions(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        # Aggregate distribution collection and distribution snippets
        # Note: these snippets are not localised (yet), but we still need to upload
        # 4 lang versions to please the CF function language hack
        self.print("Generating distribution records...")
        if options["sample"]:
            datasets = Dataset.objects.filter(dataset_id__in=SAMPLE_IDS)
        else:
            datasets = Dataset.objects.all()
        for dataset in datasets:
            self.print_success(f"Processing dataset: {dataset.dataset_id}")
            ds_distributions = list(dataset.distribution_set.all())
            for lang in LANGS:
                collection_id = f"{dataset.dataset_id}.distributions"
                distribution_collection = OARCollection(
                    id=collection_id,
                    title=f"Distribution Collection for {collection_id}",
                    lang=lang,
                    base_url=self.oar_base_url,
                )
                for distribution in ds_distributions:
                    distribution_record = OARDistribution.from_distribution(
                        distribution,
                        lang=lang,
                        collection_id=collection_id,
                        base_url=self.oar_base_url,
                    )
                    self.print_success(f" - {distribution_record.get_key()}")
                    distribution_collection.feature_collection.features.append(distribution_record)

                # Dump the generated record collections (for debugging)
                if options["dump"]:
                    self.dump_collection(distribution_collection)

                # Upload the record collections to S3
                if options["upload"]:
                    self.upload_collection(
                        distribution_collection,
                        prefix=OAR_PREFIX,
                    )

    def do_export_datasets(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        self.print("Generating dataset records...")

        if options["sample"]:
            datasets = Dataset.objects.filter(dataset_id__in=SAMPLE_IDS)
        else:
            datasets = Dataset.objects.all()

        dataset_collections = []
        for lang in LANGS:
            collection_id = "swissgeo.catalog"
            dataset_collection = OARCollection(
                id=collection_id, title="Swissgeo Catalog", lang=lang, base_url=self.oar_base_url
            )

            for dataset in datasets:
                dataset_record = OARDataset.from_dataset(
                    dataset, lang, collection_id=collection_id, base_url=self.oar_base_url
                )
                self.print(f"- {dataset_record.get_key()}")
                dataset_collection.feature_collection.features.append(dataset_record)

            # Dump the generated record collections (for debugging)
            if options["dump"]:
                self.dump_collection(dataset_collection)

            # Upload the record collections to S3
            if options["upload"]:
                self.upload_collection(
                    dataset_collection,
                    prefix=OAR_PREFIX,
                )

            dataset_collections.append(dataset_collection)

    def do_export_landing_page(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        # Landing page
        self.print("Uploading landing page...")
        landing_page = {
            "title": "OGC API Records - swissgeo",
            "description": "OGC API Records implementation for swissgeo datasets and services.",
            "links": [
                {
                    "href": "https://swissgeo-services.apidog.io",
                    "rel": "service-doc",
                    "type": "application/json",
                    "title": "OGC API Records - swissgeo - Documentation",
                },
                {
                    "href": f"{self.oar_base_url}/collections",
                    "rel": "data",
                    "type": "application/json",
                    "title": "Swissgeo Catalog Collection",
                },
                {
                    "href": f"{self.oar_base_url}/conformance",
                    "rel": "conformance",
                    "type": "application/json",
                    "title": "Conformance Declaration",
                },
            ],
        }
        self.upload_object(key=f"{OAR_PREFIX}/landingpage", obj=landing_page)

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
            self.upload_object(
                key=f"{OAR_PREFIX}/conformance.{lang}",
                obj=conformance_declaration,
            )

        # /collections endpoint
        self.print("Uploading collections endpoint...")
        for lang in LANGS:
            collections = {
                "collections": [
                    {
                        "id": "swissgeo.catalog",
                        "title": "Swissgeo Catalog",
                        "description": "Collection of all swissgeo datasets",
                        "itemType": "record",
                        "links": [
                            {
                                "href": (
                                    f"{self.oar_base_url}/collections/swissgeo.catalog?language={lang}"
                                ),
                                "rel": "self",
                                "title": "This record",
                                "type": "application/json",
                                "hreflang": lang,
                            },
                            *[
                                {
                                    "href": (
                                        f"{self.oar_base_url}/collections/swissgeo.catalog?language={alt}"
                                    ),
                                    "rel": "alternate",
                                    "title": f"This record ({value.alternate})",
                                    "type": "application/json",
                                    "hreflang": alt,
                                }
                                for alt, value in LANGS.items()
                                if alt != lang
                            ],
                            {
                                "href": (
                                    f"{self.oar_base_url}/collections/swissgeo.catalog/items?language={lang}"
                                ),
                                "rel": "items",
                                "type": "application/json",
                                "hreflang": lang,
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
                                "href": (
                                    f"{self.oar_base_url}/collections/geoadmin.services?language={lang}"
                                ),
                                "rel": "self",
                                "title": "This record",
                                "type": "application/json",
                                "hreflang": lang,
                            },
                            *[
                                {
                                    "href": (
                                        f"{self.oar_base_url}/collections/geoadmin.services?language={alt}"
                                    ),
                                    "rel": "alternate",
                                    "title": f"This record ({value.alternate})",
                                    "type": "application/json",
                                    "hreflang": alt,
                                }
                                for alt, value in LANGS.items()
                                if alt != lang
                            ],
                        ],
                    },
                ],
                "links": [
                    {
                        "href": f"{self.oar_base_url}/collections?language={lang}",
                        "rel": "self",
                        "description": "This document",
                        "type": "application/json",
                        "hreflang": lang,
                    },
                    *[
                        {
                            "href": f"{self.oar_base_url}/collections?language={alt}",
                            "rel": "alternate",
                            "description": f"This document {value.alternate}",
                            "type": "application/json",
                            "hreflang": alt,
                        }
                        for alt, value in LANGS.items()
                        if alt != lang
                    ],
                ],
            }
            self.upload_object(
                key=f"{OAR_PREFIX}/collections.{lang}",
                obj=collections,
            )

        self.print_success("Export completed.")
        # endregion

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
