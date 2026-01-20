import json
from typing import Any

import environ
import requests
from config.settings_base import BASE_DIR
from tinydb import Query
from tinydb import TinyDB
from utils.command import CustomBaseCommand

env = environ.Env()


class Command(CustomBaseCommand):
    """Manage OGC API Records Content.

    Currently, this command harvests various sources, merges their content,
    and writes static OGC API Records compliant JSON files to S3

    """

    help = "OAR management"

    def add_arguments(self, parser):

        # Sub-commands
        sub = parser.add_subparsers(dest="command", required=False, help="Sub-commands")

        harvest = sub.add_parser("harvest", help="Download data files from various sources")
        harvest.add_argument(
            "-s",
            "--sources",
            choices=["layersconfig", "mapserverlayers", "all"],
            nargs='+',
            required=True,
            help="Source to harvest from"
        )

        imp = sub.add_parser("import", help="Import the source APIs into a local database (TinyDB)")
        imp.add_argument(
            "-s",
            "--sources",
            choices=["layersconfig", "mapserverlayers", "all"],
            nargs='+',
            required=True,
            help="Source to harvest from"
        )

        merge = sub.add_parser(
            "merge", help="Merge and convert data in the database to OGC API Records format"
        )
        merge.add_argument(
            "-l",
            "--limit",
            type=int,
            default=None,
            help="Limit number of records to merge (for testing)"
        )

        export = sub.add_parser(
            "export", help="Export data in the database to OGC API Records format file"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        # initialize temporary local file-bases databases
        # Note: usage of TinyDB is just for prototyping purposes and current state of initial development.
        # It will likely be replaced by either directly populating Models in service-control and/or
        # have some kind of generic harvesting mechanism that detects changes and updates only changed records.
        self.harvest_db = TinyDB(
            BASE_DIR / 'harvest' / 'db_harvest_db.json', sort_keys=True, indent=4
        )
        self.table_layersconfig = self.harvest_db.table('layersconfig')
        self.table_mapserverlayers = self.harvest_db.table('mapserverlayers')

        self.records_db = TinyDB(
            BASE_DIR / 'harvest' / 'db_records_swissgeo.json', sort_keys=True, indent=4
        )
        self.table_records = self.records_db.table('records')

        self.distributions_db = TinyDB(
            BASE_DIR / 'harvest' / 'db_records_distributions.json', sort_keys=True, indent=4
        )
        self.distribution_collections = self.distributions_db.table('collections')

        self.styles_db = TinyDB(BASE_DIR / 'harvest' / 'db_styles.json', sort_keys=True, indent=4)
        self.table_styles = self.styles_db.table('styles')

        # Show parsed arguments (useful for debugging)
        if options.get('verbosity', 0) >= 2:
            print("Debug: parsed args =", args)

        # Handle sub-commands
        if options['command'] == "harvest":
            self.do_harvest(*args, **options)
        if options['command'] == "import":
            self.do_import(*args, **options)
        if options['command'] == "merge":
            self.do_merge(*args, **options)
        # TODO: the export command is not yet transferred since it likely will get major changes
        # anyway with writing files to S3 instead of local filesystem
        # if options['command'] == "export":
        #     self.do_export(*args, **options)

    # ##########################################################################
    def do_harvest(self, *args: Any, **options: Any) -> None:
        #region Harvesting
        self.print_success(f"Harvesting from sources: {options['sources']}")

        def harvest_layersconfig():
            self.print("Harvesting from layersConfig source...")

            response = requests.get(
                "https://api3.geo.admin.ch/rest/services/all/MapServer/layersConfig?lang=en",
                timeout=30
            )
            layers = response.json()
            with open(BASE_DIR / "harvest" / "layersConfig_en.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(layers, indent=2, ensure_ascii=False))

        def harvest_mapserverlayers():
            # https://api3.geo.admin.ch/rest/services/api/MapServer
            self.print("Harvesting from mapserverlayers source...")

            response = requests.get(
                "https://api3.geo.admin.ch/rest/services/api/MapServer?lang=en", timeout=30
            )
            mapserverlayers = response.json()
            with open(BASE_DIR / "harvest" / "mapserverlayers_en.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(mapserverlayers, indent=2, ensure_ascii=False))

        if "layersconfig" in options['sources'] or "all" in options['sources']:
            harvest_layersconfig()
        if "mapserverlayers" in options['sources'] or "all" in options['sources']:
            harvest_mapserverlayers()

        return 0

        #endregion

    # ##########################################################################
    def do_import(self, *args: Any, **options: Any) -> None:
        #region Importing
        self.print_success(f"Importing from sources: {options['sources']}")

        def import_layersconfig(args) -> int:
            print("Importing layersConfig...")

            with open("harvest/layersConfig_en.json", "r", encoding="utf-8") as f:
                layers = json.loads(f.read())

            for layername, layer in layers.items():
                layer['id'] = layername
                self.table_layersconfig.upsert(layer, Query().id == layername)

        def import_mapserverlayers(args) -> int:

            print("Importing MapServer layers...")

            with open("harvest/mapserverlayers_en.json", "r", encoding="utf-8") as f:
                mapserverlayers = json.loads(f.read())

            for layer in mapserverlayers["layers"]:
                layer_id = layer.get('layerBodId', None)
                layer['id'] = layer_id
                self.table_mapserverlayers.upsert(layer, Query().id == layer_id)

        if "layersconfig" in options['sources'] or "all" in options['sources']:
            import_layersconfig(args)
        if "mapserverlayers" in options['sources'] or "all" in options['sources']:
            import_mapserverlayers(args)

        #endregion

    # ##########################################################################
    def do_merge(self, *args: Any, **options: Any) -> None:
        #region Merging
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
            if options['limit'] and _idx >= options['limit']:
                print(f"++++ Limiting to {options['limit']} records for testing purposes")
                break
            layer_id = layersconfig_entry.get('serverLayerName', None)
            print(layer_id)

            dataset = Dataset(_id=layer_id)

            mapserver_entry = self.table_mapserverlayers.get(Query().id == layer_id)
            if not mapserver_entry:
                print(f"++++ WARNING: layer {layer_id} not found in mapserverlayers")
                mapserver_entry = {'attributes': {}}

            # Language
            # TODO: generalize to support multiple languages
            dataset.properties['language'] = {"code": "en", "name": "English", "dir": "ltr"}

            # Contact
            contact_name = mapserver_entry['attributes'].get('dataOwner', None)
            if not contact_name:
                print(f"++++ WARNING: layer {layer_id} has no contact info")
            else:
                contact = {"organisation": contact_name}
                contact['country'] = 'CH'
                contact['role'] = 'dataOwner'
                dataset.properties['contacts'] = [contact]

            # Attribution is not part of OGC API Records standard
            # but exists as stac extension
            # https://github.com/stac-extensions/attribution
            dataset.properties['attribution'] = mapserver_entry['attributes'].get(
                'dataOwner', "ERR:NO_ATTRIBUTION"
            )
            # We add also an attribution link if available
            if 'attributionUrl' in layersconfig_entry:
                dataset.add_link(
                    Link(
                        href=layersconfig_entry['attributionUrl'],
                        rel="attribution",
                        typ="text/html",
                        title="Attribution"
                    )
                )

            # Description
            dataset.properties['description'] = mapserver_entry['attributes'].get(
                'abstract', 'ERR:NO_DESCRIPTION'
            )

            # Title
            if 'name' in mapserver_entry and mapserver_entry['name'] != layersconfig_entry['label']:
                print(
                    f"++++ WARNING: layer {layer_id} name mismatch: {mapserver_entry['name']} != {layersconfig_entry['label']}"
                )
            dataset.properties['title'] = layersconfig_entry.get('label', 'ERR:NO_TITLE')

            # Keywords

            # ----------------------------------------------------------------
            # Links
            #region
            dataset.add_link(
                Link(
                    href=f"collections/swissgeo.catalog/items/{layer_id}",
                    rel="self",
                    typ="application/json"
                )
            )

            dataset.add_link(
                Link(href="collections/swissgeo.catalog", rel="collection", typ="application/json")
            )

            dataset.add_link(
                Link(
                    href=f'collections/{layer_id}',
                    rel="distributions",
                    typ="application/json",
                    title="Distributions"
                )
            )

            # Link to description page
            if 'urldetails' in mapserver_entry['attributes']:
                dataset.add_link(
                    Link(
                        href=mapserver_entry['attributes']['urlDetails'],
                        rel="describedby",
                        typ="text/html",
                        title="Details"
                    )
                )

            # Link to geocat metadata
            if 'idGeoCat' in mapserver_entry:
                dataset.add_link(
                    Link(
                        href=
                        f"https://www.geocat.ch/geonetwork/srv/ger/catalog.search#/metadata/{mapserver_entry.get('idGeoCat')}",
                        rel="alternate",
                        title="GeoCat Metadata",
                        typ="text/html"
                    )
                )

            #endregion

            self.table_records.upsert(dataset.as_dict(), Query().id == layer_id)

            # ----------------------------------------------------------------
            #region Merging: Distributions
            dataset_link = Link(f"collections/swissgeo.catalog/items/{layer_id}", rel="dataset")

            distribution_id = layersconfig_entry.get('serverLayerName', None) or layer_id

            distributionCollection = Collection(_id=layer_id, title=f"Distributions for {layer_id}")

            if layersconfig_entry['type'].lower() == 'wmts':
                wmts_distribution_id = distribution_id + ':wmts'
                distribution = WMTSDistribution(
                    _id=wmts_distribution_id, dataset_id=layer_id, external_id=layer_id
                )
                distribution.add_link(dataset_link)

                # Opacity can be seen as a styling hint. We create separate 'style'
                # files for layers with non-default opacity (or gutters for WMS layers).
                # Those files are following the Maplibre style specification (as far as
                # possible, e.g. 'gutter' is not part of the spec).
                # see https://maplibre.org/maplibre-style-spec/layers/#raster
                if 'opacity' in layersconfig_entry and layersconfig_entry['opacity'] < 1.0:
                    style_id = f"{wmts_distribution_id}.style"
                    style = {
                        "layers": [{
                            "id": style_id,
                            "source": "wmts.geo.admin.ch",
                            "type": "raster",
                            "paint": {
                                "raster-opacity": layersconfig_entry['opacity']
                            }
                        }]
                    }
                    # don't write style files directly for the moment
                    # with open(f"styles/{style_id}", "w", encoding="utf-8") as f:
                    #     f.write(json.dumps(style, indent=2, ensure_ascii=False))
                    style["id"] = style_id
                    self.table_styles.insert(style)

                    distribution.add_link(
                        Link(
                            href=f"styles/{style_id}",
                            rel="styledby",
                            typ="application/json",
                            title="Style Hints for WMTS Raster Layer (Maplibre Style Spec)"
                        )
                    )

                # If the layer type is 'wmts', then the wmts distribution is the preferred
                # one to use in the application.
                distributionCollection.portal["preferredDistributionId"] = wmts_distribution_id

                distributionCollection.add_record(distribution)

            # if type is wms or wmts, we create a WMS distribution as well
            if layersconfig_entry['type'].lower() in ['wms', 'wmts']:
                wms_distribution_id = distribution_id + ':wms'
                wms_distribution = WMSDistribution(
                    _id=wms_distribution_id, dataset_id=layer_id, external_id=layer_id
                )
                wms_distribution.add_link(dataset_link)

                if layersconfig_entry['type'].lower() == 'wms':
                    # If the layer type is 'wms', then the wms distribution is the preferred
                    # one to use in the application.
                    distributionCollection.portal["preferredDistributionId"] = wms_distribution_id

                    # Create style file if gutter or opacity are defined
                    if 'gutter' in layersconfig_entry or 'opacity' in layersconfig_entry:
                        style_id = f"{wms_distribution_id}.style"
                        style = {
                            "layers": [{
                                "id": style_id,
                                "source": "wms.geo.admin.ch",
                                "type": "raster",
                                "paint": {}
                            }]
                        }

                        # Note that `raster-gutter` is not part of the Maplibre style spec
                        if 'gutter' in layersconfig_entry:
                            style['layers'][0]['paint']['raster-gutter'] = layersconfig_entry[
                                'gutter']
                        if 'opacity' in layersconfig_entry:
                            style['layers'][0]['paint']['raster-opacity'] = layersconfig_entry[
                                'opacity']

                        with open(f"styles/{style_id}", "w", encoding="utf-8") as f:
                            f.write(json.dumps(style, indent=2, ensure_ascii=False))
                        wms_distribution.add_link(
                            Link(
                                href=f"styles/{style_id}",
                                rel="styledby",
                                typ="application/json",
                                title="Style Hints for WMS Raster Layer (Maplibre Style Spec)"
                            )
                        )

                distributionCollection.add_record(wms_distribution)

            if layersconfig_entry['type'].lower() == 'geojson':
                geojson_distribution_id = distribution_id + ':geojson'
                geojson_distribution = GeoJSONDistribution(
                    _id=geojson_distribution_id,
                    geojson_url=layersconfig_entry['geojsonUrl'],
                    dataset_id=layer_id,
                    external_id=layer_id,
                    title="GeoJSON Feature Service"
                )
                geojson_distribution.properties['protocol'] = "OGC:GeoJSON"
                geojson_distribution.add_link(dataset_link)

                # Add style link
                # Note: for some reason the styleUrl doesn't contain the protocol
                # (https:// or http://), so we add it here
                if not layersconfig_entry['styleUrl'].startswith('http'):
                    style_url = 'https:' + layersconfig_entry['styleUrl']
                else:
                    style_url = layersconfig_entry['styleUrl']
                geojson_distribution.add_link(
                    Link(
                        href=style_url,
                        rel="styledby",
                        typ="application/json",
                        title="GeoJSON Style Definition"
                    )
                )
                distributionCollection.add_record(geojson_distribution)

            if 'downloadUrl' in mapserver_entry['attributes']:
                stac_distribution_id = distribution_id + ':stac'
                stac_distribution = STACDistribution(
                    _id=stac_distribution_id, dataset_id=layer_id, external_id=layer_id
                )
                stac_distribution.add_link(dataset_link)
                distributionCollection.add_record(stac_distribution)
            #endregion

            self.distribution_collections.upsert(
                distributionCollection.as_dict(), Query().id == layer_id
            )

        return 0

    #endregion


# ##########################################################################
#region Class Definitions
# ##########################################################################


class Link:

    def __init__(self, href: str, rel: str, title: str = None, typ: str = None):
        self.href = href
        self.rel = rel
        self.title = title
        self.type = typ

    def as_dict(self) -> dict:
        dct = {"href": self.href, "rel": self.rel}
        if self.title:
            dct['title'] = self.title
        if self.type:
            dct['type'] = self.type
        return dct


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

    def add_record(self, record: 'Record'):
        self.records.append(record)

    def as_dict(self) -> dict:
        dct = {
            "id": self.id,
            "title": self.title,
            'type': 'Collection',
            'itemType': 'record',
            "recordsArrayName": "records",
            "records": [record.as_dict() for record in self.records]
        }
        if self.portal:
            dct['portal'] = self.portal

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
        """ initialize a Distribution

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
            Link(
                href=f"collections/{self.dataset_id}/items/{self.id}",
                rel="self",
                typ="application/json"
            )
        )


class WMTSDistribution(Distribution):
    protocol = "OGC:WMTS"

    def __init__(self, title: str = "OGC Web Map Tile Service (WMTS)", **kwargs):
        super().__init__(title=title, **kwargs)
        self.add_link(
            Link(href="collections/geoadmin.services/items/ch.admin.geo.wmts", rel="service")
        )


class WMSDistribution(Distribution):
    protocol = "OGC:WMS"

    def __init__(self, title: str = "OGC Web Map Service (WMS)", **kwargs):
        super().__init__(title=title, **kwargs)
        self.add_link(
            Link(href="collections/geoadmin.services/items/ch.admin.geo.wms", rel="service")
        )


class STACDistribution(Distribution):
    protocol = "OGC:STAC"

    def __init__(self, title: str = "STAC Download Service", **kwargs):
        super().__init__(title=title, **kwargs)
        self.add_link(
            Link(href="collections/geoadmin.services/items/ch.admin.geo.data", rel="service")
        )


class GeoJSONDistribution(Distribution):
    protocol = "OGC:GeoJSON"

    def __init__(self, geojson_url: str, title: str = "GeoJSON Feature Service", **kwargs):
        super().__init__(title=title, **kwargs)
        self.geojson_url = geojson_url
        self.add_link(Link(href=self.geojson_url, rel="data", typ="application/geo+json"))


#endregion
