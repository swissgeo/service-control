# pylint: disable=W,C,R
# ruff: noqa
# type: ignore
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

harvest_dir = BASE_DIR / "harvest"
harvest_dir.mkdir(exist_ok=True)

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

# use SSO session to start since this will be executed locally for the moment
boto3.setup_default_session(profile_name="swisstopo-swissgeo-dev")


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

        harvest = sub.add_parser("harvest", help="Download data files from various sources")
        harvest.add_argument(
            "-s",
            "--sources",
            choices=["layersconfig", "mapserverlayers", "all"],
            nargs="+",
            default=["all"],
            help="Source to harvest from",
        )

        convert = sub.add_parser(
            "convert", help="Convert harvested data to internal json-db format"
        )
        convert.add_argument(
            "-s",
            "--sources",
            choices=["layersconfig", "mapserverlayers", "all"],
            nargs="+",
            default=["all"],
            help="Source to harvest from",
        )

        imp = sub.add_parser("import", help="Import the source APIs into a local database (TinyDB)")
        imp.add_argument(
            "-s",
            "--sources",
            choices=["layersconfig", "mapserverlayers", "all"],
            nargs="+",
            default=["all"],
            help="Source to harvest from",
        )
        imp.add_argument(
            "--samples-only",
            action="store_true",
            help="Import only sample records (for testing)",
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

        upload = sub.add_parser(
            "upload", help="Upload data in the database to OGC API Records format file"
        )
        upload.add_argument(
            "--records-bucket",
            type=str,
            default="oa-records-static-dev-swissgeo",
            help="S3 Bucket to upload exported OARecords files to",
        )
        upload.add_argument(
            "--styles-bucket",
            type=str,
            default="oa-styles-static-dev-swissgeo",
            help="S3 Bucket to upload exported OARecords styles to",
        )
        upload.add_argument(
            "--fixtures",
            action="store_true",
            help="Upload fixtures only",
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

        self.db_datasets = TinyDB(harvest_dir / "db_datasets.json", sort_keys=True, indent=4)
        self.tbl_datasets = self.db_datasets.table("datasets")

        self.db_distributions = TinyDB(
            harvest_dir / "db_distributions.json", sort_keys=True, indent=4
        )
        self.tbl_distributions = self.db_distributions.table("distributions")

        self.records_db = TinyDB(harvest_dir / "db_records_datasets.json", sort_keys=True, indent=4)
        self.oar_dataset_de = self.records_db.table("datasets_de")
        self.oar_dataset_fr = self.records_db.table("datasets_fr")
        self.oar_dataset_it = self.records_db.table("datasets_it")
        self.oar_dataset_en = self.records_db.table("datasets_en")

        self.distributions_db = TinyDB(
            harvest_dir / "db_records_distributions.json", sort_keys=True, indent=4
        )
        self.oar_distributions_de = self.distributions_db.table("distributions_de")
        self.oar_distributions_fr = self.distributions_db.table("distributions_fr")
        self.oar_distributions_it = self.distributions_db.table("distributions_it")
        self.oar_distributions_en = self.distributions_db.table("distributions_en")

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
        if options["command"] == "convert":
            self.do_convert(*args, **options)
        if options["command"] == "import":
            self.do_import_datasets(*args, **options)
            self.do_import_distributions(*args, **options)
        if options["command"] == "merge":
            self.do_merge_legacy(*args, **options)
        if options["command"] == "export":
            self.do_export(*args, **options)
        if options["command"] == "upload":
            if options["fixtures"]:
                self.do_upload_fixtures(*args, **options)
            else:
                self.do_upload(*args, **options)
        if options["command"] == "clean":
            self.do_clean(*args, **options)

    # ##########################################################################
    def do_harvest(self, *args: Any, **options: Any) -> None:
        # region Harvesting
        self.print_success(
            f"Harvesting from sources: {options['sources']} for languages {options['lang']}"
        )

        def harvest_layersconfig():
            self.print("Harvesting from layersConfig source...")

            for lang in options["lang"]:
                self.print(f" - Language: {lang}")
                response = requests.get(
                    f"https://api3.geo.admin.ch/rest/services/all/MapServer/layersConfig?language={lang}",
                    timeout=30,
                )
                layers = response.json()
                with open(harvest_dir / f"layersConfig_{lang}.json", "w", encoding="utf-8") as f:
                    f.write(json.dumps(layers, indent=2, ensure_ascii=False))

        def harvest_mapserverlayers():
            # https://api3.geo.admin.ch/rest/services/api/MapServer
            self.print("Harvesting from mapserverlayers source...")

            for lang in options["lang"]:
                self.print(f" - Language: {lang}")
                response = requests.get(
                    f"https://api3.geo.admin.ch/rest/services/api/MapServer?language={lang}",
                    timeout=30,
                )
                mapserverlayers = response.json()
                with open(harvest_dir / f"mapserverlayers_{lang}.json", "w", encoding="utf-8") as f:
                    f.write(json.dumps(mapserverlayers, indent=2, ensure_ascii=False))

        if "layersconfig" in options["sources"] or "all" in options["sources"]:
            harvest_layersconfig()
        if "mapserverlayers" in options["sources"] or "all" in options["sources"]:
            harvest_mapserverlayers()

        # endregion

    # ##########################################################################
    def do_convert(self, *args: Any, **options: Any) -> None:
        # region Converting
        self.print_success(
            f"Converting from sources: {options['sources']} for languages {options['lang']}"
        )

        def convert_layersconfig(args) -> int:
            self.print("Truncating existing entries...")
            self.table_layersconfig.truncate()
            self.print("Converting layersConfig...")

            for lang in options["lang"]:
                self.print(f" - Language: {lang}")
                with open(harvest_dir / f"layersConfig_{lang}.json", "r", encoding="utf-8") as f:
                    layers = json.loads(f.read())

                for layername, layer in layers.items():
                    layer["language"] = lang
                    layer["id"] = layername
                    self.table_layersconfig.insert(layer)

        def convert_mapserverlayers(args) -> int:
            self.print("Truncating existing entries...")
            self.table_mapserverlayers.truncate()
            self.print("Converting MapServer layers...")

            for lang in options["lang"]:
                self.print(f" - Language: {lang}")
                with open(
                    BASE_DIR / "harvest" / f"mapserverlayers_{lang}.json", "r", encoding="utf-8"
                ) as f:
                    mapserverlayers = json.loads(f.read())

                for layer in mapserverlayers["layers"]:
                    layer_id = layer.get("layerBodId", None)
                    layer["language"] = lang
                    layer["id"] = layer_id
                    self.table_mapserverlayers.insert(layer)

        if "layersconfig" in options["sources"] or "all" in options["sources"]:
            convert_layersconfig(args)
        if "mapserverlayers" in options["sources"] or "all" in options["sources"]:
            convert_mapserverlayers(args)

        # endregion

    # ##########################################################################
    def do_import_datasets(self, *args: Any, **options: Any) -> None:
        # region Importing Datasets
        """Import data from various harvested files into local data structures"""
        self.print_success(
            f"Importing from sources: {options['sources']} for languages {options['lang']}"
        )
        self.tbl_datasets.truncate()

        # Loop over a sample or all layers in layersconfig
        # construct queryset
        if options["samples_only"]:
            layersconfig_qs = self.table_layersconfig.search(Query().id.one_of(SAMPLE_IDS))
        else:
            layersconfig_qs = self.table_layersconfig.all()

        for layersconfig_entry in layersconfig_qs:
            layer_id = layersconfig_entry.get("id")
            lang = layersconfig_entry.get("language")  # having no language would be an error here

            qs = self.tbl_datasets.search(Query().id == layersconfig_entry.get("id"))
            if qs:
                self.print(f" - Updating existing dataset: {layersconfig_entry.get('id')}")
                ds = Dataset(**qs[0])
            else:
                self.print(f" - Creating new dataset: {layersconfig_entry.get('id')}")
                ds = Dataset(id=layersconfig_entry.get("id"))

            # Get corresponding mapserverlayers entry
            mapserver_entry = self.table_mapserverlayers.get(
                (Query().id == layer_id) & (Query().language == layersconfig_entry.get("language"))
            )
            if not mapserver_entry:
                self.print_warning(f"++++ WARNING: layer {layer_id} not found in mapserverlayers")
                mapserver_entry = {"attributes": {}}

            # Title
            if "name" in mapserver_entry and mapserver_entry["name"] != layersconfig_entry["label"]:
                self.print_warning(
                    f"++++ WARNING: layer {layer_id} name mismatch: {mapserver_entry['name']} != {layersconfig_entry['label']}"
                )
            setattr(ds, f"title_{lang}", layersconfig_entry.get("label", "ERR:NO_TITLE"))

            # Description
            setattr(
                ds,
                f"description_{lang}",
                mapserver_entry["attributes"].get("abstract", "ERR:NO_DESCRIPTION"),
            )

            # Contact
            contact_name = mapserver_entry["attributes"].get("dataOwner", None)
            if not contact_name:
                self.print_warning(f"++++ WARNING: layer {layer_id} has no contact info")
            else:
                contacts = getattr(ds, f"contacts_{lang}")
                contacts.append(Contact(organisation=contact_name, country="CH", role="dataOwner"))

            # Geocat ID
            if "idGeoCat" in mapserver_entry:
                ds.geocat_id = mapserver_entry.get("idGeoCat")

            # ----------------------------------------------------------------
            # Links
            links = getattr(ds, f"links_{lang}")

            # Self link is only added during export for specific language
            links.append(
                Link(
                    href=f"{OAR_BASE_URL}/collections/swissgeo.catalog/items/{layer_id}?language={lang}",
                    rel="self",
                    typ="application/json",
                    title="This Record",
                )
            )

            # Catalog
            links.append(
                Link(
                    href=f"{OAR_BASE_URL}/collections/swissgeo.catalog?language={lang}",
                    rel="collection",
                    typ="application/json",
                    title="Swissgeo Catalog",
                )
            )

            # Distributions
            links.append(
                Link(
                    href=f"{OAR_BASE_URL}/collections/{layer_id}?language={lang}",
                    rel="distributions",
                    typ="application/json",
                    title="Distributions",
                )
            )

            # Details
            if "urlDetails" in mapserver_entry["attributes"]:
                links.append(
                    Link(
                        href=mapserver_entry["attributes"]["urlDetails"],
                        rel="describedby",
                        typ="text/html",
                        title="Details",
                    )
                )

            # GeoCat Alternate
            if "idGeoCat" in mapserver_entry:
                links.append(
                    Link(
                        href=f"https://www.geocat.ch/geonetwork/srv/{LANGS_GEOCAT[lang]}/catalog.search#/metadata/{mapserver_entry.get('idGeoCat')}",
                        rel="alternate",
                        title="GeoCat Metadata",
                        typ="text/html",
                    )
                )

            # If the layer type is 'wmts', then the wmts distribution is the preferred
            # one to use in the application.
            distribution_id = layersconfig_entry.get("serverLayerName", None) or layer_id
            if layersconfig_entry["type"].lower() in ["wmts", "wms"]:
                ds.preferred_distribution_id = (
                    distribution_id + ":" + layersconfig_entry["type"].lower()
                )

            self.tbl_datasets.upsert(
                ds.model_dump(by_alias=True), Query().id == layersconfig_entry.get("id")
            )
        # endregion

    # ##########################################################################
    def do_import_distributions(self, *args: Any, **options: Any) -> None:
        # region Importing Distributions
        """Import data from various harvested files into local data structures"""
        self.print_success(
            f"Importing distributions data from sources: {options['sources']} for languages {options['lang']}"
        )
        self.tbl_distributions.truncate()

        # Loop over a sample or all layers in layersconfig
        # construct queryset
        if options["samples_only"]:
            layersconfig_qs = self.table_layersconfig.search(Query().id.one_of(SAMPLE_IDS))
        else:
            layersconfig_qs = self.table_layersconfig.all()

        for layersconfig_entry in layersconfig_qs:
            layer_id = layersconfig_entry.get("id")
            distribution_id = layersconfig_entry.get("serverLayerName", None) or layer_id
            lang = layersconfig_entry.get("language")  # having no language would be an error here

            dataset_link = Link(
                href=f"{OAR_BASE_URL}/collections/swissgeo.catalog/items/{layer_id}?language={lang}",
                rel="dataset",
                hreflang=lang,
                typ="application/json",
                title="Dataset Record",
            )

            # region WMTS Distribution
            if layersconfig_entry["type"].lower() == "wmts":
                wmts_distribution_id = layer_id + ":wmts"

                qs = dtb = None

                qs = self.tbl_distributions.search(Query().id == wmts_distribution_id)

                if qs:
                    self.print(f" - Updating existing distribution: {wmts_distribution_id}")
                    dtb = Distribution(**qs[0])
                else:
                    self.print(f" - Creating new distribution: {wmts_distribution_id}")
                    dtb = Distribution(
                        id=wmts_distribution_id,
                        dataset_id=layer_id,
                        external_id=distribution_id,
                        protocol="OGC:WMTS",
                    )

                setattr(dtb, f"title_{lang}", f"OGC Web Map Tile Service (WMTS)")

                links = getattr(dtb, f"links_{lang}")
                # Link to dataset
                links.append(dataset_link)
                links.append(
                    Link(
                        href=f"{OAR_BASE_URL}/collections/geoadmin.services/items/ch.admin.geo.wmts",
                        rel="service",
                    )
                )

                # Opacity can be seen as a styling hint. We create separate 'style'
                # files for layers with non-default opacity (or gutters for WMS layers).
                # Those files are following the Maplibre style specification (as far as
                # possible, e.g. 'gutter' is not part of the spec).
                # see https://maplibre.org/maplibre-style-spec/layers/#raster
                if "opacity" in layersconfig_entry and layersconfig_entry["opacity"] < 1.0:
                    style_id = f"{wmts_distribution_id}:style"
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

                    style["id"] = style_id
                    self.table_styles.upsert(style, Query().id == style_id)

                    links.append(
                        Link(
                            href=f"{OAS_BASE_URL}/styles/{style_id}",
                            rel="styledby",
                            typ="application/json",
                            title="Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
                        )
                    )

                self.tbl_distributions.upsert(
                    dtb.model_dump(by_alias=True), Query().id == wmts_distribution_id
                )
            # endregion

            # region WMS Distribution
            # if type is wms or wmts, we create a WMS distribution as well
            if layersconfig_entry["type"].lower() in ["wms", "wmts"]:
                wms_distribution_id = distribution_id + ":wms"

                qs = dtb = None
                qs = self.tbl_distributions.search(Query().id == wms_distribution_id)
                if qs:
                    self.print(f" - Updating existing distribution: {wms_distribution_id}")
                    dtb = Distribution(**qs[0])
                else:
                    self.print(f" - Creating new distribution: {wms_distribution_id}")
                    dtb = Distribution(
                        id=wms_distribution_id,
                        dataset_id=layer_id,
                        external_id=layer_id,
                        protocol="OGC:WMS",
                    )

                # Set Title
                setattr(dtb, f"title_{lang}", f"OGC Web Map Service (WMS)")

                links = getattr(dtb, f"links_{lang}")
                # Link to dataset
                links.append(dataset_link)
                links.append(
                    Link(
                        href=f"{OAR_BASE_URL}/collections/geoadmin.services/items/ch.admin.geo.wms",
                        rel="service",
                    )
                )

                if layersconfig_entry["type"].lower() == "wms":
                    # Create style file if gutter or opacity are defined
                    if "gutter" in layersconfig_entry or "opacity" in layersconfig_entry:
                        style_id = f"{wms_distribution_id}:style"
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
                        self.table_styles.upsert(style, Query().id == style_id)

                        links.append(
                            Link(
                                href=f"{OAS_BASE_URL}/styles/{style_id}",
                                rel="styledby",
                                typ="application/json",
                                title="Style Hints for WMS Raster Layer (Maplibre Style Spec)",
                            )
                        )

                self.tbl_distributions.upsert(
                    dtb.model_dump(by_alias=True), Query().id == wms_distribution_id
                )
            # endregion

            # region GeoJSON Distribution
            if layersconfig_entry["type"].lower() == "geojson":
                geojson_distribution_id = distribution_id + ":geojson"

                qs = dtb = None
                qs = self.tbl_distributions.search(Query().id == geojson_distribution_id)
                if qs:
                    self.print(f" - Updating existing distribution: {geojson_distribution_id}")
                    dtb = Distribution(**qs[0])
                else:
                    self.print(f" - Creating new distribution: {geojson_distribution_id}")
                    dtb = Distribution(
                        id=geojson_distribution_id,
                        dataset_id=layer_id,
                        external_id=layer_id,
                        protocol="OGC:GeoJSON",
                    )

                # Set Title
                setattr(dtb, f"title_{lang}", f"GeoJSON Feature Service")

                links = getattr(dtb, f"links_{lang}")
                links.append(dataset_link)
                # Link to geojson data
                links.append(
                    Link(
                        href=layersconfig_entry["geojsonUrl"],
                        rel="data",
                        typ="application/geo+json",
                        title="GeoJSON Feature Data",
                    )
                )

                # Add style link
                # Note: for some reason the styleUrl doesn't contain the protocol
                # (https:// or http://), so we add it here
                if not layersconfig_entry["styleUrl"].startswith("http"):
                    style_url = "https:" + layersconfig_entry["styleUrl"]
                else:
                    style_url = layersconfig_entry["styleUrl"]
                links.append(
                    Link(
                        href=style_url,
                        rel="styledby",
                        typ="application/json",
                        title="GeoJSON Style Definition",
                    )
                )

                self.tbl_distributions.upsert(
                    dtb.model_dump(by_alias=True), Query().id == geojson_distribution_id
                )
            # endregion

            # region STAC Distribution
            # Get corresponding mapserverlayers entry
            mapserver_entry = self.table_mapserverlayers.get(
                (Query().id == layer_id) & (Query().language == layersconfig_entry.get("language"))
            )
            if not mapserver_entry:
                self.print_warning(f"++++ WARNING: layer {layer_id} not found in mapserverlayers")
                mapserver_entry = {"attributes": {}}

            if "downloadUrl" in mapserver_entry["attributes"]:
                stac_distribution_id = distribution_id + ":stac"

                qs = dtb = None
                qs = self.tbl_distributions.search(Query().id == stac_distribution_id)
                if qs:
                    self.print(f" - Updating existing distribution: {stac_distribution_id}")
                    dtb = Distribution(**qs[0])
                else:
                    self.print(f" - Creating new distribution: {stac_distribution_id}")
                    dtb = Distribution(
                        id=stac_distribution_id,
                        dataset_id=layer_id,
                        external_id=layer_id,
                        protocol="OGC:STAC",
                    )

                # Set Title
                setattr(dtb, f"title_{lang}", f"STAC Download Service")

                links = getattr(dtb, f"links_{lang}")
                links.append(dataset_link)
                links.append(
                    Link(
                        href=f"{OAR_BASE_URL}/collections/geoadmin.services/items/ch.admin.geo.data",
                        rel="service",
                    )
                )

                self.tbl_distributions.upsert(
                    dtb.model_dump(by_alias=True), Query().id == stac_distribution_id
                )
            # endregion

        # endregion

    # ##########################################################################
    def do_merge_legacy(self, *args: Any, **options: Any) -> None:
        # region ====Merging
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
            # region ====Links
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
            # region ====Merging: Distributions
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
        # region Export
        self.print_success("Starting to export local data to OGC API Records format...")

        # Export Datasets to OAR Records format
        self.print("Exporting Datasets to OAR Records format...")
        for lang in options["lang"]:
            table = getattr(self, f"oar_dataset_{lang}")
            table.truncate()
            oar_distribution_table = getattr(self, f"oar_distributions_{lang}")
            oar_distribution_table.truncate()

        for _ds in self.tbl_datasets.all():
            ds = Dataset(**_ds)
            for lang in options["lang"]:
                table = getattr(self, f"oar_dataset_{lang}")
                oar_record = ds.as_oar_record(lang=lang)
                table.insert(oar_record.model_dump(exclude_none=True, by_alias=True))

                # Find all distributions for this dataset and this language and
                # create a distribution collection for them
                oar_distribution_table = getattr(self, f"oar_distributions_{lang}")
                distribution_collection = OARCollection(
                    id=ds.id, title=f"Distributions for {ds.id}"
                )
                for _dist in self.tbl_distributions.search(Query().dataset_id == ds.id):
                    dist = Distribution(**_dist).as_oar_record(lang=lang)

                    distribution_collection.records.append(dist)
                oar_distribution_table.insert(
                    distribution_collection.model_dump(exclude_none=True, by_alias=True)
                )

    # endregion

    # ##########################################################################
    def do_upload(self, *args: Any, **options: Any) -> None:
        # region Upload
        self.print_success("Starting to upload local OGC API Records to S3...")

        # setup boto3 s3 client
        oarecords_s3_bucket = options["records_bucket"]
        styles_s3_bucket = options["styles_bucket"]

        # Upload dataset records
        self.print_success("Starting to upload dataset records...")
        for lang in options["lang"]:
            table = getattr(self, f"oar_dataset_{lang}")
            catalogCollection = OARCollection(id="swissgeo.catalog", title="Swissgeo Catalog")
            # Add links
            catalogCollection.links.append(
                Link(
                    href=f"{OAR_BASE_URL}/collections/swissgeo.catalog?language={lang}",
                    rel="self",
                    typ="application/json",
                    title="Swissgeo Catalog",
                )
            )

            # Add records
            for _record in table.all():
                self.print(f"Record ID: {_record['id']}, Title: {_record['properties']['title']}")
                record = OARDataset(**_record)

                # Add record to catalog collection
                catalogCollection.records.append(record)

                # Upload as well the single dataset records
                self.s3_client.put_object(
                    Bucket=oarecords_s3_bucket,
                    Key=f"{OAR_PREFIX}/collections/swissgeo.catalog/items/{record.id}.{lang}",
                    Body=json.dumps(
                        record.model_dump(exclude_none=True, by_alias=True),
                        indent=2,
                        ensure_ascii=False,
                    ).encode("utf-8"),
                    ContentType="application/json",
                )
            self.print("Uploading dataset collection record...")
            self.s3_client.put_object(
                Bucket=oarecords_s3_bucket,
                Key=f"{OAR_PREFIX}/collections/swissgeo.catalog.{lang}",
                Body=json.dumps(
                    catalogCollection.model_dump(exclude_none=True, by_alias=True),
                    indent=2,
                    ensure_ascii=False,
                ).encode("utf-8"),
                ContentType="application/json",
            )
        self.print_success("Dataset records upload completed.")

        # Upload distribution collections
        self.print_success(f"Upload Distributions Collections")
        for lang in options["lang"]:
            table = getattr(self, f"oar_distributions_{lang}")
            for distribution in table.all():
                self.print(f" - {OAR_PREFIX}/collections/{distribution['id']}.{lang}")

                self.s3_client.put_object(
                    Bucket=oarecords_s3_bucket,
                    Key=f"{OAR_PREFIX}/collections/{distribution['id']}.{lang}",
                    Body=json.dumps(distribution, indent=2, ensure_ascii=False).encode("utf-8"),
                    ContentType="application/json",
                )

        # # Upload styles
        self.print(f"Uploading styles...")
        for style in self.table_styles.all():
            self.print(f" - {OAS_PREFIX}/styles/{style['id']}")

            self.s3_client.put_object(
                Bucket=styles_s3_bucket,
                Key=f"{OAS_PREFIX}/styles/{style['id']}",
                Body=json.dumps(style, indent=2, ensure_ascii=False).encode("utf-8"),
                ContentType="application/json",
            )

    # ##########################################################################
    def do_upload_fixtures(self, *args: Any, **options: Any) -> None:
        # region Upload
        self.print_success("Starting to upload local OGC API Records to S3...")

        # setup boto3 s3 client
        oarecords_s3_bucket = options["records_bucket"]
        styles_s3_bucket = options["styles_bucket"]

        # Write service files
        # Note: these snippets are not localised (yet), but we still need to upload
        # 4 lang versions to please the CF function language hack
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
        for lang in LANGS.keys():
            self.s3_client.put_object(
                Bucket=oarecords_s3_bucket,
                Key=f"{OAR_PREFIX}/collections/geoadmin.services/items/ch.admin.geo.data.{lang}",
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
        for lang in LANGS.keys():
            self.s3_client.put_object(
                Bucket=oarecords_s3_bucket,
                Key=f"{OAR_PREFIX}/collections/geoadmin.services/items/ch.admin.geo.wms.{lang}",
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
        for lang in LANGS.keys():
            self.s3_client.put_object(
                Bucket=oarecords_s3_bucket,
                Key=f"{OAR_PREFIX}/collections/geoadmin.services/items/ch.admin.geo.wmts.{lang}",
                Body=json.dumps(geoadmin_wmts_service, indent=2, ensure_ascii=False).encode(
                    "utf-8"
                ),
                ContentType="application/json",
            )

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
            Bucket=oarecords_s3_bucket,
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
                Bucket=oarecords_s3_bucket,
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
                Bucket=oarecords_s3_bucket,
                Key=f"{OAR_PREFIX}/collections.{lang}",
                Body=json.dumps(collections, indent=2, ensure_ascii=False).encode("utf-8"),
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


class OARRecord(BaseModel):
    id: str
    links: list[Link] = Field(default_factory=list)
    type: Literal["Feature"] = "Feature"
    geometry: Optional[dict] = None

    # def __init__(self, _id: str):
    #     super().__init__()
    #     self.id = _id
    #     self.links = []
    #     self.properties = {"type": self.typ}

    # def add_link(self, link: Link):
    #     self.links.append(link)

    # def as_dict(self) -> dict:
    #     dct = {"links": []}
    #     for link in self.links:
    #         dct["links"].append(link.as_dict())
    #     dct["id"] = self.id
    #     dct["properties"] = self.properties
    #     return dct


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

    # def __init__(self, _id: str, dataset_id: str, external_id: str, title: str):
    #     """initialize a Distribution

    #     Args:
    #         _id (str): internal identifier of the distribution
    #         dataset_id (str): dataset identifier to which this distribution belongs
    #         external_id (str): external identifier of the distribution (e.g. layer id), i.e. this is the identifier used e.g. in the Capabilities XML.
    #         title (str): title of the distribution

    #     """
    #     super().__init__(_id=_id)
    #     self.properties["externalIds"] = [external_id]
    #     self.dataset_id = dataset_id
    #     self.properties["title"] = title
    #     self.properties["protocol"] = self.protocol

    #     self.add_link(
    #         OARLink(
    #             href=f"collections/{self.dataset_id}/items/{self.id}",
    #             rel="self",
    #             typ="application/json",
    #         )
    #     )


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

    # def __init__(self, _id: str, title: str):
    #     super().__init__()
    #     self.id = _id
    #     self.title = title
    #     self.records = []
    #     self.portal = {}

    # def add_record(self, record: "Record"):
    #     self.records.append(record)

    # def as_dict(self) -> dict:
    #     dct = {
    #         "id": self.id,
    #         "title": self.title,
    #         "type": "Collection",
    #         "itemType": "record",
    #         "recordsArrayName": "records",
    #         "records": [record.as_dict() for record in self.records],
    #     }
    #     if self.portal:
    #         dct["portal"] = self.portal

    #     return dct


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


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid")  # forbid extra fields not defined in the model

    id: str = Field(frozen=True)  # make id field immutable
    # note: this could be UUID but gives troubles when serializing to dict
    # hence we use str for the moment
    # geocat_id: Optional[uuid.UUID] = None
    geocat_id: Optional[str] = None

    title_de: Optional[str] = None
    title_fr: Optional[str] = None
    title_it: Optional[str] = None
    title_en: Optional[str] = None

    description_de: Optional[str] = None
    description_fr: Optional[str] = None
    description_it: Optional[str] = None
    description_en: Optional[str] = None

    links_de: list[Link] = Field(default_factory=list)
    links_fr: list[Link] = Field(default_factory=list)
    links_it: list[Link] = Field(default_factory=list)
    links_en: list[Link] = Field(default_factory=list)

    preferred_distribution_id: Optional[str] = None

    contacts_de: list[Contact] = Field(default_factory=list)
    contacts_fr: list[Contact] = Field(default_factory=list)
    contacts_it: list[Contact] = Field(default_factory=list)
    contacts_en: list[Contact] = Field(default_factory=list)

    def as_oar_record(self, lang: str) -> OARDataset:
        record = OARDataset(id=self.id)

        # Set properties
        record.properties["title"] = getattr(self, f"title_{lang}", None)
        record.properties["description"] = getattr(self, f"description_{lang}", None)
        record.properties["preferredDistributionId"] = self.preferred_distribution_id
        record.properties["language"] = LANGS[lang]
        record.properties["languages"] = list(LANGS.values())
        record.properties["contacts"] = getattr(self, f"contacts_{lang}", [])

        # Add links
        links = getattr(self, f"links_{lang}", [])
        for link in links:
            record.links.append(link)

        return record


class Distribution(BaseModel):
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

    id: str
    dataset_id: str
    external_id: str
    protocol: str

    title_de: Optional[str] = None
    title_fr: Optional[str] = None
    title_it: Optional[str] = None
    title_en: Optional[str] = None

    links_de: list[Link] = Field(default_factory=list)
    links_fr: list[Link] = Field(default_factory=list)
    links_it: list[Link] = Field(default_factory=list)
    links_en: list[Link] = Field(default_factory=list)

    def as_oar_record(self, lang: str) -> OARDistribution:
        record = OARDistribution(id=self.id)

        # Set properties
        record.properties["type"] = "Distribution"
        record.properties["protocol"] = self.protocol
        record.properties["title"] = getattr(self, f"title_{lang}", None)

        # Add links
        links = getattr(self, f"links_{lang}", [])
        for link in links:
            record.links.append(link)

        return record


class LegacyLink:
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


class OARLink(LegacyLink):
    """OAR Link

    An OAR Link is a Link with correct host and prefix added to the href.

    """

    def __init__(self, href: str, **kwargs):
        full_href = f"https://services.{ENV_HOSTNAME_POSTFIX}/{OAR_PREFIX}/{href}"
        super().__init__(full_href, **kwargs)


class OASLink(LegacyLink):
    """OAS Link

    An OAS Link is a Link with correct host and prefix added to the href.

    """

    def __init__(self, href: str, **kwargs):
        full_href = f"https://services.{ENV_HOSTNAME_POSTFIX}/{OAS_PREFIX}/{href}"
        super().__init__(full_href, **kwargs)


# class WMTSDistribution(OARDistribution):
#     protocol: str = "OGC:WMTS"

#     def __init__(self, title: str = "OGC Web Map Tile Service (WMTS)", **kwargs):
#         super().__init__(title=title, **kwargs)
#         self.add_link(
#             OARLink(href="collections/geoadmin.services/items/ch.admin.geo.wmts", rel="service")
#         )


# class WMSDistribution(OARDistribution):
#     protocol: str = "OGC:WMS"

#     def __init__(self, title: str = "OGC Web Map Service (WMS)", **kwargs):
#         super().__init__(title=title, **kwargs)
#         self.add_link(
#             OARLink(href="collections/geoadmin.services/items/ch.admin.geo.wms", rel="service")
#         )


# class STACDistribution(OARDistribution):
#     protocol: str = "OGC:STAC"

#     def __init__(self, title: str = "STAC Download Service", **kwargs):
#         super().__init__(title=title, **kwargs)
#         self.add_link(
#             OARLink(href="collections/geoadmin.services/items/ch.admin.geo.data", rel="service")
#         )


# class GeoJSONDistribution(OARDistribution):
#     protocol: str = "OGC:GeoJSON"

#     def __init__(self, geojson_url: str, title: str = "GeoJSON Feature Service", **kwargs):
#         super().__init__(title=title, **kwargs)
#         self.geojson_url = geojson_url
#         self.add_link(Link(href=self.geojson_url, rel="data", typ="application/geo+json"))


# endregion
