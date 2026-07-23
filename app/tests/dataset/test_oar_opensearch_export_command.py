from dataservice.models import WMSDataservice
from dataset.management.commands.oar_opensearch_export import Command
from dataset.models import Dataset
from distribution.models import ExternalWMSDistribution

OAR_BASE_URL = "https://services.dev.sgdi.tech/api/oar/staticv2"
OAS_BASE_URL = "https://services.dev.sgdi.tech/api/oas/v0"


def _make_dataservice() -> WMSDataservice:
    dataservice = WMSDataservice(
        dataservice_id="wmts-geoadminch",
        title="WMTS geo.admin.ch",
        documentation_url_de="https://docs.geo.admin.ch/visualize-data/wmts.html",
        languages=["de", "fr", "en", "it"],
        capabilities_url="https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang={lang}",
    )
    dataservice.save()
    return dataservice


def _make_dataset() -> Dataset:
    dataset = Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="Rote Liste Moose",
        title_short_fr="Liste rouge mousses",
        title_short_en="Red list bryophytes",
        title_short_it="Lista rossa biofite",
        description_de="Beschreibung",
        description_fr="Description",
        description_en="Description",
        description_it="Descrizione",
        geocat_id="07b046a7-1b21-4cd0-b605-a113f2e5e94d",
    )
    dataset.save()
    return dataset


def test_build_service_doc(db):
    doc = Command().build_service_doc(_make_dataservice(), OAR_BASE_URL)

    assert doc["id"] == "wmts-geoadminch"
    assert doc["type"] == "Feature"
    # Multilingual title object, service type as a keyword.
    assert doc["properties"] == {
        "type": "ogc:wms",
        "title": {
            "de": "WMTS geo.admin.ch",
            "fr": "WMTS geo.admin.ch",
            "it": "WMTS geo.admin.ch",
            "en": "WMTS geo.admin.ch",
        },
    }
    # The per-language 'alternate' self links are dropped; the (de) self/collection and the
    # external links are kept.
    rels = [link["rel"] for link in doc["links"]]
    assert "alternate" not in rels
    assert rels == ["self", "collection", "service-doc", "about"]
    assert doc["linkTemplates"] == []


def test_build_dataset_doc(db):
    doc = Command().build_dataset_doc(_make_dataset(), OAR_BASE_URL)

    assert doc["$schema"].endswith("recordGeoJSON.yaml")
    assert doc["id"] == "ch.bafu.moose"
    assert doc["type"] == "Feature"
    assert doc["geometry"]["type"] == "Polygon"

    # Only external links survive, plus the (relative) distributions link.
    assert doc["links"] == [
        {
            "href": "https://www.geocat.ch/geonetwork/srv/ger/catalog.search#/metadata/07b046a7-1b21-4cd0-b605-a113f2e5e94d",
            "rel": "alternate",
            "title": "GeoCat Metadata",
            "type": "text/html",
        },
        {
            "href": "/collections/swissgeo-distributions/items/ch.bafu.moose",
            "rel": "distributions",
            "title": "Distributions",
        },
    ]

    # 'title'/'description' become multilingual objects; the singular 'language' is dropped.
    assert "language" not in doc["properties"]
    assert doc["properties"]["type"] == "Dataset"
    assert doc["properties"]["title"] == {
        "de": "Rote Liste Moose",
        "fr": "Liste rouge mousses",
        "it": "Lista rossa biofite",
        "en": "Red list bryophytes",
    }
    assert doc["properties"]["description"] == {
        "de": "Beschreibung",
        "fr": "Description",
        "it": "Descrizione",
        "en": "Description",
    }


def test_build_distribution_doc(db):
    dataservice = _make_dataservice()
    dataset = _make_dataset()
    ExternalWMSDistribution(
        distribution_id="ch.bafu.moose:wms",
        dataset=dataset,
        title_de="WMS Layer (DE)",
        title_fr="WMS Layer (FR)",
        title_it="WMS Layer (IT)",
        title_en="WMS Layer (EN)",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_it="Description (IT)",
        description_en="Description (EN)",
        dataservice=dataservice,
        wms_layer_name_de="ch.bafu.moose",
        opacity=1.0,
        gutter=0,
    ).save()

    doc = Command().build_distribution_doc(dataset, OAR_BASE_URL, OAS_BASE_URL)

    assert doc["id"] == "ch.bafu.moose"
    assert doc["type"] == "FeatureCollection"
    assert doc["properties"]["title"] == {
        "de": "Rote Liste Moose",
        "fr": "Liste rouge mousses",
        "it": "Lista rossa biofite",
        "en": "Red list bryophytes",
    }

    assert len(doc["features"]) == 1
    feature = doc["features"][0]
    assert feature["id"] == "ch.bafu.moose:wms"
    assert feature["type"] == "Feature"
    # dataset/dataservice links rewritten to relative index paths; styledby kept (language
    # stripped); the internal self/collection/featureinfo links are dropped.
    assert feature["links"] == [
        {
            "href": "/collections/swissgeo-catalog/items/ch.bafu.moose",
            "rel": "dataset",
            "title": "Dataset Record",
        },
        {
            "href": "/collections/geoadmin-services/items/wmts-geoadminch",
            "rel": "dataservice",
        },
        {
            "href": "https://services.dev.sgdi.tech/api/oas/v0/styles/ch.bafu.moose:wms:style",
            "rel": "styledby",
            "title": "Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
            "type": "application/json",
        },
    ]
    # Translated fields are {lang: value} objects, like datasets/services.
    assert feature["properties"]["type"] == "Distribution"
    assert feature["properties"]["protocol"] == "ogc:wms"
    assert feature["properties"]["externalIds"] == ["ch.bafu.moose"]
    assert feature["properties"]["title"] == {
        "de": "WMS Layer (DE)",
        "fr": "WMS Layer (FR)",
        "it": "WMS Layer (IT)",
        "en": "WMS Layer (EN)",
    }
    assert feature["properties"]["description"] == {
        "de": "Description (DE)",
        "fr": "Description (FR)",
        "it": "Description (IT)",
        "en": "Description (EN)",
    }
