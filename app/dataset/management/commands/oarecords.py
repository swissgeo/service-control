# pylint: disable=W,C,R
# ruff: noqa
# type: ignore
import json
import pathlib
from typing import Any

import boto3
import environ
import requests
from botocore.client import Config
from config.settings_base import BASE_DIR
from tinydb import Query, TinyDB
from utils.command import CustomBaseCommand

harvest_dir = BASE_DIR / "harvest"
harvest_dir.mkdir(exist_ok=True)

env = environ.Env()

OAR_PREFIX = "api/oar/v0"
OAS_PREFIX = "api/oas/v0"
ENV_HOSTNAME_POSTFIX = "dev.sgdi.tech"

# use SSO session to start since this will be executed locally for the moment
boto3.setup_default_session(profile_name="swisstopo-swissgeo-dev")


class Command(CustomBaseCommand):
    """Manage OGC API Records Content.

    Currently, this command harvests various sources, merges their content,
    and writes static OGC API Records compliant JSON files to S3

    """

    help = "OAR management"

    def add_arguments(self, parser):
        # Call the base class method to get default arguments defined in the base class
        # (mainly 'logger')
        super().add_arguments(parser)

        # Sub-commands
        sub = parser.add_subparsers(dest="command", required=False, help="Sub-commands")

        harvest = sub.add_parser("harvest", help="Download data files from various sources")
        harvest.add_argument(
            "-s",
            "--sources",
            choices=["layersconfig", "mapserverlayers", "all"],
            nargs="+",
            required=True,
            help="Source to harvest from",
        )

        imp = sub.add_parser("import", help="Import the source APIs into a local database (TinyDB)")
        imp.add_argument(
            "-s",
            "--sources",
            choices=["layersconfig", "mapserverlayers", "all"],
            nargs="+",
            required=True,
            help="Source to harvest from",
        )

        merge = sub.add_parser(
            "merge", help="Merge and convert data in the database to OGC API Records format"
        )
        merge.add_argument(
            "-l",
            "--limit",
            type=int,
            default=None,
            help="Limit number of records to merge (for testing)",
        )

        export = sub.add_parser(
            "export", help="Export data in the database to OGC API Records format file"
        )
        export.add_argument(
            "--records-bucket",
            type=str,
            default="oa-records-static-dev-swissgeo",
            help="S3 Bucket to upload exported OARecords files to",
        )
        export.add_argument(
            "--styles-bucket",
            type=str,
            default="oa-styles-static-dev-swissgeo",
            help="S3 Bucket to upload exported OARecords styles to",
        )

        clean = sub.add_parser("clean", help="Delete static files from S3 buckets")
        clean.add_argument(
            "--batch-size", type=int, default=1000, help="Number of files to delete per batch"
        )
        clean.add_argument(
            "--records-bucket",
            type=str,
            default="oa-records-static-dev-swissgeo",
            help="S3 Bucket to delete exported OARecords files from",
        )
        clean.add_argument(
            "--styles-bucket",
            type=str,
            default="oa-styles-static-dev-swissgeo",
            help="S3 Bucket to delete exported OARecords styles from",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        # initialize temporary local file-bases databases
        # Note: usage of TinyDB is just for prototyping purposes and current state of initial development.
        # It will likely be replaced by either directly populating Models in service-control and/or
        # have some kind of generic harvesting mechanism that detects changes and updates only changed records.
        self.harvest_db = TinyDB(harvest_dir / "db_harvest_db.json", sort_keys=True, indent=4)
        self.table_layersconfig = self.harvest_db.table("layersconfig")
        self.table_mapserverlayers = self.harvest_db.table("mapserverlayers")

        self.records_db = TinyDB(harvest_dir / "db_records_swissgeo.json", sort_keys=True, indent=4)
        self.table_records = self.records_db.table("records")

        self.distributions_db = TinyDB(
            harvest_dir / "db_records_distributions.json", sort_keys=True, indent=4
        )
        self.distribution_collections = self.distributions_db.table("collections")

        self.styles_db = TinyDB(harvest_dir / "db_styles.json", sort_keys=True, indent=4)
        self.table_styles = self.styles_db.table("styles")

        # basic S3 access configuration
        client_access_kwargs = {
            # "endpoint_url": s3_config['S3_ENDPOINT_URL'],
            "region_name": "eu-west-1",
            "config": Config(signature_version="s3v4"),
        }
        self.s3_client = boto3.client("s3", **client_access_kwargs)

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:
            self.print(f"Debug: parsed args = {json.dumps(options)}")

        # Handle sub-commands
        if options["command"] == "harvest":
            self.do_harvest(*args, **options)
        if options["command"] == "import":
            self.do_import(*args, **options)
        if options["command"] == "merge":
            self.do_merge(*args, **options)
        if options["command"] == "export":
            self.do_export(*args, **options)
        if options["command"] == "clean":
            self.do_clean(*args, **options)

    # ##########################################################################
    def do_harvest(self, *args: Any, **options: Any) -> None:
        # region Harvesting
        self.print_success(f"Harvesting from sources: {options['sources']}")

        def harvest_layersconfig():
            self.print("Harvesting from layersConfig source...")

            response = requests.get(
                "https://api3.geo.admin.ch/rest/services/all/MapServer/layersConfig?lang=en",
                timeout=30,
            )
            layers = response.json()
            with open(harvest_dir / "layersConfig_en.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(layers, indent=2, ensure_ascii=False))

        def harvest_mapserverlayers():
            # https://api3.geo.admin.ch/rest/services/api/MapServer
            self.print("Harvesting from mapserverlayers source...")

            response = requests.get(
                "https://api3.geo.admin.ch/rest/services/api/MapServer?lang=en", timeout=30
            )
            mapserverlayers = response.json()
            with open(harvest_dir / "mapserverlayers_en.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(mapserverlayers, indent=2, ensure_ascii=False))

        if "layersconfig" in options["sources"] or "all" in options["sources"]:
            harvest_layersconfig()
        if "mapserverlayers" in options["sources"] or "all" in options["sources"]:
            harvest_mapserverlayers()

        # endregion

    # ##########################################################################
    def do_import(self, *args: Any, **options: Any) -> None:
        # region Importing
        self.print_success(f"Importing from sources: {options['sources']}")

        def import_layersconfig(args) -> int:
            self.print("Importing layersConfig...")

            with open(harvest_dir / "layersConfig_en.json", "r", encoding="utf-8") as f:
                layers = json.loads(f.read())

            for layername, layer in layers.items():
                layer["id"] = layername
                self.table_layersconfig.upsert(layer, Query().id == layername)

        def import_mapserverlayers(args) -> int:
            self.print("Importing MapServer layers...")

            with open(harvest_dir / "mapserverlayers_en.json", "r", encoding="utf-8") as f:
                mapserverlayers = json.loads(f.read())

            for layer in mapserverlayers["layers"]:
                layer_id = layer.get("layerBodId", None)
                layer["id"] = layer_id
                self.table_mapserverlayers.upsert(layer, Query().id == layer_id)

        if "layersconfig" in options["sources"] or "all" in options["sources"]:
            import_layersconfig(args)
        if "mapserverlayers" in options["sources"] or "all" in options["sources"]:
            import_mapserverlayers(args)

        # endregion

    # ##########################################################################
    def do_merge(self, *args: Any, **options: Any) -> None:
        # region Merging
        """Merge and convert data in the database to OGC API Records format

        Merges data from the layersconfig and mapserverlayers tables in the harvest_db
        TinyDB database, and creates OGC API Records in the db_records_swissgeo.json
        database.

        """

        self.print_success("Merging records...")

        # Setup
        self.print("Merging data from different sources.")
        self.print("Truncating existing records...")
        self.table_records.truncate()
        self.distributions_db.drop_tables()
        self.table_styles.truncate()

        # Loop over all layers in layersconfig
        for _idx, layersconfig_entry in enumerate(self.table_layersconfig.all()):
            if options["limit"] and _idx >= options["limit"]:
                self.print(f"++++ Limiting to {options['limit']} records for testing purposes")
                break
            layer_id = layersconfig_entry.get("serverLayerName", None)
            self.print(f" - {layer_id}")

            dataset = Dataset(_id=layer_id)

            mapserver_entry = self.table_mapserverlayers.get(Query().id == layer_id)
            if not mapserver_entry:
                self.print_warning(f"++++ WARNING: layer {layer_id} not found in mapserverlayers")
                mapserver_entry = {"attributes": {}}

            # Language
            # TODO: generalize to support multiple languages
            dataset.properties["language"] = {"code": "en", "name": "English", "dir": "ltr"}

            # Contact
            contact_name = mapserver_entry["attributes"].get("dataOwner", None)
            if not contact_name:
                self.print_warning(f"++++ WARNING: layer {layer_id} has no contact info")
            else:
                contact = {"organisation": contact_name}
                contact["country"] = "CH"
                contact["role"] = "dataOwner"
                dataset.properties["contacts"] = [contact]

            # Attribution is not part of OGC API Records standard
            # but exists as stac extension
            # https://github.com/stac-extensions/attribution
            dataset.properties["attribution"] = mapserver_entry["attributes"].get(
                "dataOwner", "ERR:NO_ATTRIBUTION"
            )
            # We add also an attribution link if available
            if "attributionUrl" in layersconfig_entry:
                if not layersconfig_entry["attributionUrl"].startswith("http"):
                    self.print_warning(
                        f"+++ WARNING: layer {layer_id} attributionUrl does not start with http(s): {layersconfig_entry['attributionUrl']}"
                    )
                    layersconfig_entry["attributionUrl"] = (
                        "http://invalid.domain/" + layersconfig_entry["attributionUrl"]
                    )

                dataset.add_link(
                    Link(
                        href=layersconfig_entry["attributionUrl"],
                        rel="attribution",
                        typ="text/html",
                        title="Attribution",
                    )
                )

            # Description
            dataset.properties["description"] = mapserver_entry["attributes"].get(
                "abstract", "ERR:NO_DESCRIPTION"
            )

            # Title
            if "name" in mapserver_entry and mapserver_entry["name"] != layersconfig_entry["label"]:
                self.print_warning(
                    f"++++ WARNING: layer {layer_id} name mismatch: {mapserver_entry['name']} != {layersconfig_entry['label']}"
                )
            dataset.properties["title"] = layersconfig_entry.get("label", "ERR:NO_TITLE")

            # Keywords

            # ----------------------------------------------------------------
            # Links
            # region
            dataset.add_link(
                OARLink(
                    href=f"collections/swissgeo.catalog/items/{layer_id}",
                    rel="self",
                    typ="application/json",
                )
            )

            dataset.add_link(
                OARLink(
                    href="collections/swissgeo.catalog", rel="collection", typ="application/json"
                )
            )

            dataset.add_link(
                OARLink(
                    href=f"collections/{layer_id}",
                    rel="distributions",
                    typ="application/json",
                    title="Distributions",
                )
            )

            # Link to description page
            if "urldetails" in mapserver_entry["attributes"]:
                dataset.add_link(
                    Link(
                        href=mapserver_entry["attributes"]["urlDetails"],
                        rel="describedby",
                        typ="text/html",
                        title="Details",
                    )
                )

            # Link to geocat metadata
            if "idGeoCat" in mapserver_entry:
                dataset.add_link(
                    Link(
                        href=f"https://www.geocat.ch/geonetwork/srv/ger/catalog.search#/metadata/{mapserver_entry.get('idGeoCat')}",
                        rel="alternate",
                        title="GeoCat Metadata",
                        typ="text/html",
                    )
                )

            # endregion

            self.table_records.upsert(dataset.as_dict(), Query().id == layer_id)

            # ----------------------------------------------------------------
            # region Merging: Distributions
            dataset_link = OARLink(f"collections/swissgeo.catalog/items/{layer_id}", rel="dataset")

            distribution_id = layersconfig_entry.get("serverLayerName", None) or layer_id

            distributionCollection = Collection(_id=layer_id, title=f"Distributions for {layer_id}")

            if layersconfig_entry["type"].lower() == "wmts":
                wmts_distribution_id = distribution_id + ":wmts"
                distribution = WMTSDistribution(
                    _id=wmts_distribution_id, dataset_id=layer_id, external_id=layer_id
                )
                distribution.add_link(dataset_link)

                # Opacity can be seen as a styling hint. We create separate 'style'
                # files for layers with non-default opacity (or gutters for WMS layers).
                # Those files are following the Maplibre style specification (as far as
                # possible, e.g. 'gutter' is not part of the spec).
                # see https://maplibre.org/maplibre-style-spec/layers/#raster
                if "opacity" in layersconfig_entry and layersconfig_entry["opacity"] < 1.0:
                    style_id = f"{wmts_distribution_id}.style"
                    style = {
                        "layers": [
                            {
                                "id": style_id,
                                "source": "wmts.geo.admin.ch",
                                "type": "raster",
                                "paint": {"raster-opacity": layersconfig_entry["opacity"]},
                            }
                        ]
                    }
                    # don't write style files directly for the moment
                    # with open(f"styles/{style_id}", "w", encoding="utf-8") as f:
                    #     f.write(json.dumps(style, indent=2, ensure_ascii=False))
                    style["id"] = style_id
                    self.table_styles.insert(style)

                    distribution.add_link(
                        OASLink(
                            href=f"styles/{style_id}",
                            rel="styledby",
                            typ="application/json",
                            title="Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
                        )
                    )

                # If the layer type is 'wmts', then the wmts distribution is the preferred
                # one to use in the application.
                distributionCollection.portal["preferredDistributionId"] = wmts_distribution_id

                distributionCollection.add_record(distribution)

            # if type is wms or wmts, we create a WMS distribution as well
            if layersconfig_entry["type"].lower() in ["wms", "wmts"]:
                wms_distribution_id = distribution_id + ":wms"
                wms_distribution = WMSDistribution(
                    _id=wms_distribution_id, dataset_id=layer_id, external_id=layer_id
                )
                wms_distribution.add_link(dataset_link)

                if layersconfig_entry["type"].lower() == "wms":
                    # If the layer type is 'wms', then the wms distribution is the preferred
                    # one to use in the application.
                    distributionCollection.portal["preferredDistributionId"] = wms_distribution_id

                    # Create style file if gutter or opacity are defined
                    if "gutter" in layersconfig_entry or "opacity" in layersconfig_entry:
                        style_id = f"{wms_distribution_id}.style"
                        style = {
                            "layers": [
                                {
                                    "id": style_id,
                                    "source": "wms.geo.admin.ch",
                                    "type": "raster",
                                    "paint": {},
                                }
                            ]
                        }

                        # Note that `raster-gutter` is not part of the Maplibre style spec
                        if "gutter" in layersconfig_entry:
                            style["layers"][0]["paint"]["raster-gutter"] = layersconfig_entry[
                                "gutter"
                            ]
                        if "opacity" in layersconfig_entry:
                            style["layers"][0]["paint"]["raster-opacity"] = layersconfig_entry[
                                "opacity"
                            ]

                        style["id"] = style_id
                        self.table_styles.insert(style)

                        wms_distribution.add_link(
                            OASLink(
                                href=f"styles/{style_id}",
                                rel="styledby",
                                typ="application/json",
                                title="Style Hints for WMS Raster Layer (Maplibre Style Spec)",
                            )
                        )

                distributionCollection.add_record(wms_distribution)

            if layersconfig_entry["type"].lower() == "geojson":
                geojson_distribution_id = distribution_id + ":geojson"
                geojson_distribution = GeoJSONDistribution(
                    _id=geojson_distribution_id,
                    geojson_url=layersconfig_entry["geojsonUrl"],
                    dataset_id=layer_id,
                    external_id=layer_id,
                    title="GeoJSON Feature Service",
                )
                geojson_distribution.properties["protocol"] = "OGC:GeoJSON"
                geojson_distribution.add_link(dataset_link)

                # Add style link
                # Note: for some reason the styleUrl doesn't contain the protocol
                # (https:// or http://), so we add it here
                if not layersconfig_entry["styleUrl"].startswith("http"):
                    style_url = "https:" + layersconfig_entry["styleUrl"]
                else:
                    style_url = layersconfig_entry["styleUrl"]
                geojson_distribution.add_link(
                    Link(
                        href=style_url,
                        rel="styledby",
                        typ="application/json",
                        title="GeoJSON Style Definition",
                    )
                )
                distributionCollection.add_record(geojson_distribution)

            if "downloadUrl" in mapserver_entry["attributes"]:
                stac_distribution_id = distribution_id + ":stac"
                stac_distribution = STACDistribution(
                    _id=stac_distribution_id, dataset_id=layer_id, external_id=layer_id
                )
                stac_distribution.add_link(dataset_link)
                distributionCollection.add_record(stac_distribution)
            # endregion

            self.distribution_collections.upsert(
                distributionCollection.as_dict(), Query().id == layer_id
            )

        return 0

    # endregion

    # ##########################################################################
    def do_export(self, *args: Any, **options: Any) -> None:
        # region Exporting
        self.print_success("Starting to export local data to OGC API Records files on S3...")

        # setup boto3 s3 client
        oarecords_s3_bucket = options["records_bucket"]
        styles_s3_bucket = options["styles_bucket"]

        # Export catalog records
        self.print("Exporting catalog records...")
        catalogCollection = Collection(_id="swissgeo.catalog", title="Swissgeo Catalog").as_dict()
        for record in self.table_records.all():
            self.print(f"Record ID: {record['id']}, Title: {record['properties']['title']}")
            catalogCollection["records"].append(record)

        self.s3_client.put_object(
            Bucket=oarecords_s3_bucket,
            Key=f"{OAR_PREFIX}/collections/swissgeo.catalog",
            Body=json.dumps(catalogCollection, indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )

        # Export distribution collections
        self.print(f"Generate Distributions Collections")
        for distribution in self.distributions_db.table("collections").all():
            self.print(f" - {OAR_PREFIX}/collections/{distribution['id']}")

            self.s3_client.put_object(
                Bucket=oarecords_s3_bucket,
                Key=f"{OAR_PREFIX}/collections/{distribution['id']}",
                Body=json.dumps(distribution, indent=2, ensure_ascii=False).encode("utf-8"),
                ContentType="application/json",
            )

        # Export styles
        self.print(f"Export styles...")
        for style in self.table_styles.all():
            self.print(f" - {OAS_PREFIX}/styles/{style['id']}")

            self.s3_client.put_object(
                Bucket=styles_s3_bucket,
                Key=f"{OAS_PREFIX}/styles/{style['id']}",
                Body=json.dumps(style, indent=2, ensure_ascii=False).encode("utf-8"),
                ContentType="application/json",
            )

        # Write service files
        self.print("Writing service files...")
        geadmin_data_service = {
            "id": "ch.admin.geo.data",
            "links": [
                {
                    "href": "https://data.geo.admin.ch/api/stac/v1/",
                    "rel": "describes",
                    "type": "application/json",
                    "title": "STAC API Landingpage",
                }
            ],
            "properties": {"title": "Geoadmin Stac Service", "type": "ogcapi:stac"},
        }
        self.s3_client.put_object(
            Bucket=oarecords_s3_bucket,
            Key=f"{OAR_PREFIX}/collections/geoadmin.services/items/ch.admin.geo.data",
            Body=json.dumps(geadmin_data_service, indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )

        geoadmin_wms_service = {
            "id": "wms.geo.admin.ch",
            "linkTemplates": [
                {
                    "uriTemplate": "https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang={lang}",
                    "rel": "about",
                    "type": "application/xml",
                    "title": "WMS Capabilities File",
                    "variables": {
                        "lang": {
                            "description": "Language",
                            "type": "string",
                            "default": "de",
                            "enum": ["de", "fr", "en", "it"],
                        }
                    },
                }
            ],
            "properties": {"title": "WMS geo.admin.ch", "type": "ogc:wms"},
        }
        self.s3_client.put_object(
            Bucket=oarecords_s3_bucket,
            Key=f"{OAR_PREFIX}/collections/geoadmin.services/items/ch.admin.geo.wms",
            Body=json.dumps(geoadmin_wms_service, indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )

        geoadmin_wmts_service = {
            "id": "wmts.geo.admin.ch",
            "links": [
                {
                    "href": "some_url_that_does_not_exist",
                    "rel": "service-desc",
                    "type": "application/json",
                },
                {
                    "href": "https://docs.geo.admin.ch/visualize-data/wmts.html",
                    "rel": "service-doc",
                    "type": "application/json",
                },
            ],
            "linkTemplates": [
                {
                    "uriTemplate": "https://wmts.geo.admin.ch/EPSG/{EPSG}/1.0.0/WMTSCapabilities.xml",
                    "type": "application/vnd.ogc.wmts_xml",
                    "variables": {
                        "EPSG": {
                            "description": "EPSG",
                            "format": "integer",
                            "type": "number",
                            "default": 2056,
                            "enum": [2056, 21781, 4326],
                        }
                    },
                    "rel": "about",
                    "title": "WMTS Capabilities File",
                }
            ],
            "properties": {"title": "WMTS geo.admin.ch", "type": "ogc:wmts"},
        }
        self.s3_client.put_object(
            Bucket=oarecords_s3_bucket,
            Key=f"{OAR_PREFIX}/collections/geoadmin.services/items/ch.admin.geo.wmts",
            Body=json.dumps(geoadmin_wmts_service, indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )

        self.print_success("Export completed.")
        # endregion

    # ##########################################################################
    def do_clean(self, *args: Any, **options: Any) -> None:
        # region Cleaning

        for bucket in [options["records_bucket"], options["styles_bucket"]]:
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


class Link:
    def __init__(self, href: str, rel: str, title: str = None, typ: str = None):
        if not href.startswith("http"):
            raise ValueError("Link href must be a full URL starting with http:// or https://")

        self.href = href
        self.rel = rel
        self.title = title
        self.type = typ

    def as_dict(self) -> dict:
        dct = {"href": self.href, "rel": self.rel}
        if self.title:
            dct["title"] = self.title
        if self.type:
            dct["type"] = self.type
        return dct


class OARLink(Link):
    """OAR Link

    An OAR Link is a Link with correct host and prefix added to the href.

    """

    def __init__(self, href: str, **kwargs):
        full_href = f"https://services.{ENV_HOSTNAME_POSTFIX}/{OAR_PREFIX}/{href}"
        super().__init__(full_href, **kwargs)


class OASLink(Link):
    """OAS Link

    An OAS Link is a Link with correct host and prefix added to the href.

    """

    def __init__(self, href: str, **kwargs):
        full_href = f"https://services.{ENV_HOSTNAME_POSTFIX}/{OAS_PREFIX}/{href}"
        super().__init__(full_href, **kwargs)


class Collection:
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

    def __init__(self, _id: str, title: str):
        super().__init__()
        self.id = _id
        self.title = title
        self.records = []
        self.portal = {}

    def add_record(self, record: "Record"):
        self.records.append(record)

    def as_dict(self) -> dict:
        dct = {
            "id": self.id,
            "title": self.title,
            "type": "Collection",
            "itemType": "record",
            "recordsArrayName": "records",
            "records": [record.as_dict() for record in self.records],
        }
        if self.portal:
            dct["portal"] = self.portal

        return dct


class Record:
    typ = "Record"

    def __init__(self, _id: str):
        super().__init__()
        self.id = _id
        self.links = []
        self.properties = {"type": self.typ}

    def add_link(self, link: Link):
        self.links.append(link)

    def as_dict(self) -> dict:
        dct = {"links": []}
        for link in self.links:
            dct["links"].append(link.as_dict())
        dct["id"] = self.id
        dct["properties"] = self.properties
        return dct


class Dataset(Record):
    """Dataset record

    A Dataset is a Record with type="Dataset"

    """

    typ = "Dataset"


class Distribution(Record):
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

    typ = "Distribution"
    protocol = None

    def __init__(self, _id: str, dataset_id: str, external_id: str, title: str):
        """initialize a Distribution

        Args:
            _id (str): internal identifier of the distribution
            dataset_id (str): dataset identifier to which this distribution belongs
            external_id (str): external identifier of the distribution (e.g. layer id), i.e. this is the identifier used e.g. in the Capabilities XML.
            title (str): title of the distribution

        """
        super().__init__(_id=_id)
        self.properties["externalIds"] = [external_id]
        self.dataset_id = dataset_id
        self.properties["title"] = title
        self.properties["protocol"] = self.protocol

        self.add_link(
            OARLink(
                href=f"collections/{self.dataset_id}/items/{self.id}",
                rel="self",
                typ="application/json",
            )
        )


class WMTSDistribution(Distribution):
    protocol = "OGC:WMTS"

    def __init__(self, title: str = "OGC Web Map Tile Service (WMTS)", **kwargs):
        super().__init__(title=title, **kwargs)
        self.add_link(
            OARLink(href="collections/geoadmin.services/items/ch.admin.geo.wmts", rel="service")
        )


class WMSDistribution(Distribution):
    protocol = "OGC:WMS"

    def __init__(self, title: str = "OGC Web Map Service (WMS)", **kwargs):
        super().__init__(title=title, **kwargs)
        self.add_link(
            OARLink(href="collections/geoadmin.services/items/ch.admin.geo.wms", rel="service")
        )


class STACDistribution(Distribution):
    protocol = "OGC:STAC"

    def __init__(self, title: str = "STAC Download Service", **kwargs):
        super().__init__(title=title, **kwargs)
        self.add_link(
            OARLink(href="collections/geoadmin.services/items/ch.admin.geo.data", rel="service")
        )


class GeoJSONDistribution(Distribution):
    protocol = "OGC:GeoJSON"

    def __init__(self, geojson_url: str, title: str = "GeoJSON Feature Service", **kwargs):
        super().__init__(title=title, **kwargs)
        self.geojson_url = geojson_url
        self.add_link(Link(href=self.geojson_url, rel="data", typ="application/geo+json"))


# endregion
