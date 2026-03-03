import json
import pathlib
from typing import Annotated, Any, Literal, Optional

import boto3
import environ
import requests
from botocore.client import Config
from config.settings_base import BASE_DIR
from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from tinydb import Query, TinyDB
from utils.command import CustomBaseCommand

from dataset.models import Dataset
from dataservice.models import Dataservice


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

DATASETS = {}


class Lang(BaseModel):
    code: str
    name: str
    dir: str = "ltr"
    alternate: Optional[str] = None


LANGS = {
    "de": Lang(code="de", name="Deutsch", dir="ltr", alternate="German"),
    "fr": Lang(code="fr", name="Français", dir="ltr", alternate="French"),
    "it": Lang(code="it", name="Italiano", dir="ltr", alternate="Italian"),
    "en": Lang(code="en", name="English", dir="ltr"),
}

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

    def add_arguments(self, parser):
        # Call the base class method to get default arguments defined in the base class
        # (mainly 'logger')
        super().add_arguments(parser)

        # Language switch
        parser.add_argument(
            "--lang",
            type=str,
            nargs="+",
            choices=list(LANGS.keys()),
            default=["de", "fr", "it", "en"],
            help="Select the languages to use for the records (default: [de, fr, it, en])",
        )

        # Sub-commands
        sub = parser.add_subparsers(dest="command", required=False, help="Sub-commands")

        services = sub.add_parser("services", help="Export OGC API Records for services")
        services.add_argument(
            "--dump",
            action="store_true",
            help="Dump the generated records (for debugging)",
        )
        services.add_argument(
            "--upload",
            action="store_true",
            help="Upload the generated records to S3",
        )
        services.add_argument(
            "--target-env",
            type=str,
            choices=["dev", "int", "prod"],
            default="dev",
            help="Specify the target environment",
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
        if env.str("USER") != "geoadmin" and options["command"] in ("upload", "clean"):
            if options["target_env"] == "dev":
                profile_name = "swisstopo-swissgeo-dev"
            elif options["target_env"] in ["int", "prod"]:
                profile_name = "swisstopo-swissgeo"
            else:
                raise ValueError(f"Invalid target environment: {options['target_env']}")
            self.print(
                f"We're likely running this command locally, so we're using"
                f" the SSO profile {profile_name} to get a session."
            )
            self.session = boto3.Session(profile_name=profile_name)  # pylint: disable=attribute-defined-outside-init
        else:
            self.session = boto3.Session()  # pylint: disable=attribute-defined-outside-init

        # initialize temporary local file-bases databases
        # Note: usage of TinyDB is just for prototyping purposes and current state of initial development.
        # It will likely be replaced by either directly populating Models in service-control and/or
        # have some kind of generic harvesting mechanism that detects changes and updates only changed records.

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
        if options.get("verbosity", 0) >= 2:
            self.print(f"Debug: parsed args = {json.dumps(options)}")

        if options["command"] == "services":
            self.do_export_services(*args, **options)
        if options["command"] == "clean":
            self.do_clean(*args, **options)

    # ##########################################################################
    def do_export_services(self, *args: Any, **options: Any) -> None:

        services = {}

        # Write service files
        # Note: these snippets are not localised (yet), but we still need to upload
        # 4 lang versions to please the CF function language hack
        self.print("Generating service records...")
        for service in Dataservice.objects.all():
            self.print(f" - {service.dataservice_id}")
            service_record = OARDataservice.from_dataservice(service)
            services[service.dataservice_id] = service_record.model_dump(
                exclude_none=True, by_alias=True
            )

        if options["dump"]:
            self.print(json.dumps(services, indent=2, ensure_ascii=False))

        if options["upload"]:
            self.print_success("Starting to upload local OGC API Records to S3...")
            for lang in LANGS.keys():
                for service_id, service_record in services.items():
                    key = f"{OAR_PREFIX}/collections/geoadmin.services/items/{service_id}.{lang}"
                    self.s3_client.put_object(
                        Bucket=self.oarecords_s3_bucket,
                        Key=key,
                        Body=json.dumps(service_record, indent=2, ensure_ascii=False).encode(
                            "utf-8"
                        ),
                        ContentType="application/json",
                    )
                    self.print(f" - {key}")

    # ##########################################################################
    def do_export_landing_page(self, *args: Any, **options: Any) -> None:
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
        for lang in LANGS.keys():
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
        for lang in LANGS.keys():
            self.s3_client.put_object(
                Bucket=self.oarecords_s3_bucket,
                Key=f"{OAR_PREFIX}/collections.{lang}",
                Body=json.dumps(collections, indent=2, ensure_ascii=False).encode("utf-8"),
                ContentType="application/json",
            )

        self.print_success("Export completed.")
        # endregion

    # ##########################################################################
    def do_clean(self, *args: Any, **options: Any) -> None:
        buckets = []
        if options["records"]:
            buckets.append(self.oarecords_s3_bucket)
        if options["styles"]:
            buckets.append(self.oastyles_s3_bucket)

        for bucket in buckets:
            self.print_success(
                f"Cleaning bucket: {bucket}. (delete files in batches of {options['batch_size']} files)..."
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


# ##########################################################################
# region Class Definitions
# ##########################################################################


def is_url(url: str) -> str:
    if not url.startswith("http"):
        raise ValueError(f"{url} is not a valid URL")
    return url


class Link(BaseModel):
    href: Annotated[str, AfterValidator(is_url)]
    rel: str
    title: Optional[str] = None
    typ: Optional[str] = Field(default=None, serialization_alias="type")
    hreflang: Optional[str] = None


class TemplateLink(BaseModel):
    uriTemplate: str
    rel: str
    title: Optional[str] = None
    typ: Optional[str] = Field(default=None, serialization_alias="type")
    variables: Optional[dict] = None


class OARRecord(BaseModel):
    id: str
    links: list[Link] = Field(default_factory=list)
    linkTemplates: list[TemplateLink] = Field(default_factory=list)
    type: Literal["Feature"] = "Feature"
    geometry: Optional[dict] = None


class OARDataset(OARRecord):
    """Dataset record

    A Dataset is a Record with type="Dataset"

    """

    properties: dict = Field(default_factory=lambda: {"type": "Dataset"})
    geometry: Optional[dict] = {
        "type": "Polygon",
        "coordinates": [
            [[5.96, 45.82], [5.96, 47.81], [10.49, 47.81], [10.49, 45.82], [5.96, 45.82]]
        ],
    }

    @classmethod
    def from_dataset(self, ds: Dataset, lang: str) -> OARDataset:
        record = OARDataset(id=ds.dataset_id)

        # Set properties
        record.properties["title"] = getattr(ds, f"title_short_{lang}", None)
        record.properties["description"] = getattr(ds, f"description_{lang}", None)
        # record.properties["preferredDistributionId"] = self.preferred_distribution_id
        record.properties["language"] = LANGS[lang]
        record.properties["languages"] = list(LANGS.values())
        # record.properties["contacts"] = getattr(self, f"contacts_{lang}", [])

        # Add links
        # links = getattr(self, f"links_{lang}", [])
        # for link in links:
        #     record.links.append(link)

        return record


class OARDistribution(OARRecord):
    """Distribution record

    A Distribution is a Record with type="Distribution".
    Every Distribution represents one specific way to access a Dataset,
    e.g. via WMS, WMTS, STAC, etc. A Dataset can therefore have multiple
    Distribution Records.

    **Note**: We introduce here a 'protocol' property to indicate the protocol
    used to access the distribution (e.g. OGC:WMS, OGC:WMTS, OGC:STAC).
    This is not part of the OGC API Records standard, but it helps to identify
    the type of distribution. We could also include this information in the 'formats'
    property, but having a dedicated 'protocol' property makes it easier to
    query and filter distributions based on their protocol.

    """

    properties: dict = Field(default_factory=lambda: {"type": "Distribution"})


class OARDataservice(OARRecord):
    """Service record

    A Service is a Record with type="Service"
    """

    properties: dict = {}

    @classmethod
    def from_dataservice(self, ds: Dataservice, lang: str = "de") -> OARDataservice:
        record = OARDataservice(id=ds.dataservice_id)

        # Set properties
        record.properties["title"] = getattr(ds, f"title", None)
        record.properties["type"] = getattr(ds, f"type", None)

        # Add links
        if ds.service_doc:
            record.links.append(
                Link(
                    href=ds.service_doc.href,
                    rel=ds.service_doc.rel,
                    typ=ds.service_doc.link_type,
                    title=ds.service_doc.title,
                )
            )
        if ds.service_desc:
            record.links.append(
                Link(
                    href=ds.service_desc.href,
                    rel=ds.service_desc.rel,
                    typ=ds.service_desc.link_type,
                    title=ds.service_desc.title,
                )
            )
        if ds.describes:
            record.links.append(
                Link(
                    href=ds.describes.href,
                    rel=ds.describes.rel,
                    typ=ds.describes.link_type,
                    title=ds.describes.title,
                )
            )
        for template_link in ds.templated_links.all():
            record.linkTemplates.append(
                TemplateLink(
                    uriTemplate=template_link.uri_template,
                    rel=template_link.rel,
                    typ=template_link.link_type,
                    title=template_link.title,
                    variables={
                        variable_name: variable_value
                        for variable_name, variable_value in template_link.variables.all().values_list(
                            "variable_name", "variable_dict"
                        )
                    },
                )
            )

        return record


class OARCollection(BaseModel):
    """Record Collection

    The record collection entity has a slightly different structure
    than a record itself.
    Spec: https://developer.ogc.org/api/records/index.html#tag/Collection/operation/describeCollection

    Note the following:
    /collections/{collectionId} will return a Collection with roughly the following structure:
    {
      "id": "string",
      "title": "string",
      "type": "Collection",
      "itemType": "record",
      "recordsArrayName": "records",
      "records": [
        { ... Record ... }
      ]
    }

    /collections/{collectionId}/items will return a FeatureCollection with roughly
    the following structure:
    {
      "type": "FeatureCollection",
      "features": [
        { ... Record ... }
      ]
    }

    Unfortunately, the record array attribute names differ between the two endpoints.
    For now we'll implement only the /collections/{collectionId} structure and use the
    inline 'records' array. The /items endpoint will be implemented later once we have
    service-control in place to serve those endpoints. We'll then remove the inline
    'records' array from the Collection and instead add a link with rel="items" to
    point to the /items endpoint.

    """

    id: str
    title: str
    type: str = "Collection"
    itemType: str = "record"
    recordsArrayName: str = "records"
    records: list[Any] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)


class Contact(BaseModel):
    organisation: str
    country: str
    role: str
    # name: Optional[str] = None
    # position: Optional[str] = None
    # email: Optional[str] = None
    # phone: Optional[str] = None
    # address: Optional[str] = None
    # city: Optional[str] = None
    # postal_code: Optional[str] = None
