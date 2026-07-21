# ruff:noqa:E501
from io import StringIO
from json import loads
from unittest.mock import patch

from django.core.management import call_command

from dataservice.models import WMSDataservice
from dataset.models import Dataset
from distribution.models import ExternalGeoJSONDistribution, ExternalWMSDistribution


def extract_put_object(session):
    result = []
    for call in session.mock_calls:
        if "put_object" in str(call):
            kwargs = call.kwargs.copy()
            kwargs["Body"] = loads(kwargs["Body"])
            result.append(kwargs)
    return result


@patch("dataset.management.commands.oar_export.Session")
def test_command_exports_services(session, db):
    WMSDataservice(
        dataservice_id="wmts-geoadminch",
        title="WMTS geo.admin.ch",
        documentation_url_de="https://docs.geo.admin.ch/visualize-data/wmts.html",
        languages=["de", "fr", "en", "it"],
        capabilities_url="https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang={lang}",
    ).save()

    out = StringIO()
    call_command("oar_export", types=["services"], upload=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "api/oar/staticv2/collections/geoadmin.services.de" in out
    assert "api/oar/staticv2/collections/geoadmin.services/items.de" in out
    assert "api/oar/staticv2/collections/geoadmin.services.fr" in out
    assert "api/oar/staticv2/collections/geoadmin.services/items.fr" in out
    assert "api/oar/staticv2/collections/geoadmin.services.it" in out
    assert "api/oar/staticv2/collections/geoadmin.services/items.it" in out
    assert "api/oar/staticv2/collections/geoadmin.services.en" in out
    assert "api/oar/staticv2/collections/geoadmin.services/items.en" in out

    result = extract_put_object(session)
    assert result == [
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/geoadmin.services.de",
            "Body": {
                "id": "geoadmin.services",
                "title": "Geoadmin Services",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=de",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=de",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/geoadmin.services/items.de",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "wmts-geoadminch",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=de",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=fr",
                                "rel": "alternate",
                                "title": "This Record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=it",
                                "rel": "alternate",
                                "title": "This Record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=en",
                                "rel": "alternate",
                                "title": "This Record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=de",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://docs.geo.admin.ch/visualize-data/wmts.html",
                                "rel": "service-doc",
                                "title": "Service Documentation (DE)",
                                "type": "application/json",
                            },
                            {
                                "href": "https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang=de",
                                "rel": "about",
                                "title": "WMS Capabilities File",
                                "type": "application/xml",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "properties": {"title": "WMTS geo.admin.ch", "type": "ogc:wms"},
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=de",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=de",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch.de",
            "Body": {
                "id": "wmts-geoadminch",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=de",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=fr",
                        "rel": "alternate",
                        "title": "This Record (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=it",
                        "rel": "alternate",
                        "title": "This Record (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=en",
                        "rel": "alternate",
                        "title": "This Record (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=de",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://docs.geo.admin.ch/visualize-data/wmts.html",
                        "rel": "service-doc",
                        "title": "Service Documentation (DE)",
                        "type": "application/json",
                    },
                    {
                        "href": "https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang=de",
                        "rel": "about",
                        "title": "WMS Capabilities File",
                        "type": "application/xml",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "properties": {"title": "WMTS geo.admin.ch", "type": "ogc:wms"},
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/geoadmin.services.fr",
            "Body": {
                "id": "geoadmin.services",
                "title": "Geoadmin Services",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=fr",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=fr",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/geoadmin.services/items.fr",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "wmts-geoadminch",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=fr",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=de",
                                "rel": "alternate",
                                "title": "This Record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=it",
                                "rel": "alternate",
                                "title": "This Record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=en",
                                "rel": "alternate",
                                "title": "This Record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=fr",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://docs.geo.admin.ch/visualize-data/wmts.html",
                                "rel": "service-doc",
                                "title": "Service Documentation (DE)",
                                "type": "application/json",
                            },
                            {
                                "href": "https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang=fr",
                                "rel": "about",
                                "title": "WMS Capabilities File",
                                "type": "application/xml",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "properties": {"title": "WMTS geo.admin.ch", "type": "ogc:wms"},
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=fr",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=fr",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch.fr",
            "Body": {
                "id": "wmts-geoadminch",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=fr",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=de",
                        "rel": "alternate",
                        "title": "This Record (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=it",
                        "rel": "alternate",
                        "title": "This Record (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=en",
                        "rel": "alternate",
                        "title": "This Record (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=fr",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://docs.geo.admin.ch/visualize-data/wmts.html",
                        "rel": "service-doc",
                        "title": "Service Documentation (DE)",
                        "type": "application/json",
                    },
                    {
                        "href": "https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang=fr",
                        "rel": "about",
                        "title": "WMS Capabilities File",
                        "type": "application/xml",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "properties": {"title": "WMTS geo.admin.ch", "type": "ogc:wms"},
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/geoadmin.services.it",
            "Body": {
                "id": "geoadmin.services",
                "title": "Geoadmin Services",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=it",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=it",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/geoadmin.services/items.it",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "wmts-geoadminch",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=it",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=de",
                                "rel": "alternate",
                                "title": "This Record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=fr",
                                "rel": "alternate",
                                "title": "This Record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=en",
                                "rel": "alternate",
                                "title": "This Record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=it",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://docs.geo.admin.ch/visualize-data/wmts.html",
                                "rel": "service-doc",
                                "title": "Service Documentation (DE)",
                                "type": "application/json",
                            },
                            {
                                "href": "https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang=it",
                                "rel": "about",
                                "title": "WMS Capabilities File",
                                "type": "application/xml",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "properties": {"title": "WMTS geo.admin.ch", "type": "ogc:wms"},
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=it",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=it",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch.it",
            "Body": {
                "id": "wmts-geoadminch",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=it",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=de",
                        "rel": "alternate",
                        "title": "This Record (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=fr",
                        "rel": "alternate",
                        "title": "This Record (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=en",
                        "rel": "alternate",
                        "title": "This Record (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=it",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://docs.geo.admin.ch/visualize-data/wmts.html",
                        "rel": "service-doc",
                        "title": "Service Documentation (DE)",
                        "type": "application/json",
                    },
                    {
                        "href": "https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang=it",
                        "rel": "about",
                        "title": "WMS Capabilities File",
                        "type": "application/xml",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "properties": {"title": "WMTS geo.admin.ch", "type": "ogc:wms"},
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/geoadmin.services.en",
            "Body": {
                "id": "geoadmin.services",
                "title": "Geoadmin Services",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=en",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=en",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/geoadmin.services/items.en",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "wmts-geoadminch",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=en",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=de",
                                "rel": "alternate",
                                "title": "This Record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=fr",
                                "rel": "alternate",
                                "title": "This Record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=it",
                                "rel": "alternate",
                                "title": "This Record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=en",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://docs.geo.admin.ch/visualize-data/wmts.html",
                                "rel": "service-doc",
                                "title": "Service Documentation (DE)",
                                "type": "application/json",
                            },
                            {
                                "href": "https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang=en",
                                "rel": "about",
                                "title": "WMS Capabilities File",
                                "type": "application/xml",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "properties": {"title": "WMTS geo.admin.ch", "type": "ogc:wms"},
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=en",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=en",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch.en",
            "Body": {
                "id": "wmts-geoadminch",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=en",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=de",
                        "rel": "alternate",
                        "title": "This Record (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=fr",
                        "rel": "alternate",
                        "title": "This Record (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=it",
                        "rel": "alternate",
                        "title": "This Record (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=en",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://docs.geo.admin.ch/visualize-data/wmts.html",
                        "rel": "service-doc",
                        "title": "Service Documentation (DE)",
                        "type": "application/json",
                    },
                    {
                        "href": "https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang=en",
                        "rel": "about",
                        "title": "WMS Capabilities File",
                        "type": "application/xml",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "properties": {"title": "WMTS geo.admin.ch", "type": "ogc:wms"},
            },
            "ContentType": "application/json",
        },
    ]


@patch("dataset.management.commands.oar_export.Session")
def test_command_exports_wms_distribution(session, db):
    dataservice = WMSDataservice(
        dataservice_id="wmts-geoadminch",
        title="WMTS geo.admin.ch",
        documentation_url_de="https://docs.geo.admin.ch/visualize-data/wmts.html",
        languages=["de", "fr", "en", "it"],
        capabilities_url="https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang={lang}",
    )
    dataservice.save()

    dataset = Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="Rote Liste Moose (Gefährdung der Moose in der Schweiz)",
        title_short_fr="Liste rouge mousses",
        title_short_en="Red list bryophytes",
        title_short_it="Lista rossa delle biofite minacciate in Svizzera",
        title_short_rm="Glista cotschna dals mistgels (mistgels periclitads en Svizra)",
        description_de="missing",
        description_fr="missing",
        description_en="missing",
        description_it="missing",
        description_rm="missing",
        geocat_id="07b046a7-1b21-4cd0-b605-a113f2e5e94d",
    )
    dataset.save()

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

    out = StringIO()
    call_command("oar_export", types=["distributions"], upload=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions.de" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.de" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions.fr" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.fr" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions.it" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.it" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions.en" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.en" in out
    assert "api/oas/v0/styles/ch.bafu.moose:wms:style.de" in out
    assert "api/oas/v0/styles/ch.bafu.moose:wms:style.fr" in out
    assert "api/oas/v0/styles/ch.bafu.moose:wms:style.it" in out
    assert "api/oas/v0/styles/ch.bafu.moose:wms:style.en" in out

    result = extract_put_object(session)
    assert result == [
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions.de",
            "Body": {
                "id": "ch.bafu.moose.distributions",
                "title": "Distribution Collection for ch.bafu.moose.distributions",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=de",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.de",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "ch.bafu.moose:wms",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                                "rel": "alternate",
                                "title": "This Record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                                "rel": "alternate",
                                "title": "This Record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                                "rel": "alternate",
                                "title": "This Record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=de",
                                "rel": "dataset",
                                "title": "Link to parent dataset ch.bafu.moose",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=de",
                                "rel": "dataservice",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                                "rel": "featureinfo",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oas/v0/styles/ch.bafu.moose:wms:style?language=de",
                                "rel": "styledby",
                                "title": "Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "properties": {
                            "type": "Distribution",
                            "title": "WMS Layer (DE)",
                            "description": "Description (DE)",
                            "protocol": "ogc:wms",
                            "externalIds": ["ch.bafu.moose"],
                        },
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=de",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms.de",
            "Body": {
                "id": "ch.bafu.moose:wms",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                        "rel": "alternate",
                        "title": "This Record (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                        "rel": "alternate",
                        "title": "This Record (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                        "rel": "alternate",
                        "title": "This Record (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=de",
                        "rel": "dataset",
                        "title": "Link to parent dataset ch.bafu.moose",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=de",
                        "rel": "dataservice",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                        "rel": "featureinfo",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oas/v0/styles/ch.bafu.moose:wms:style?language=de",
                        "rel": "styledby",
                        "title": "Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "properties": {
                    "type": "Distribution",
                    "title": "WMS Layer (DE)",
                    "description": "Description (DE)",
                    "protocol": "ogc:wms",
                    "externalIds": ["ch.bafu.moose"],
                },
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-styles-static-dev-swissgeo",
            "Key": "api/oas/v0/styles/ch.bafu.moose:wms:style.de",
            "Body": {
                "id": "ch.bafu.moose:wms:style",
                "layers": [
                    {
                        "id": "ch.bafu.moose:wms:style",
                        "paint": {"raster-opacity": 1.0, "raster-gutter": 0},
                        "source": "wmts-geoadminch",
                        "type": "raster",
                    }
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions.fr",
            "Body": {
                "id": "ch.bafu.moose.distributions",
                "title": "Distribution Collection for ch.bafu.moose.distributions",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=fr",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.fr",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "ch.bafu.moose:wms",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                                "rel": "alternate",
                                "title": "This Record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                                "rel": "alternate",
                                "title": "This Record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                                "rel": "alternate",
                                "title": "This Record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=fr",
                                "rel": "dataset",
                                "title": "Link to parent dataset ch.bafu.moose",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=fr",
                                "rel": "dataservice",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                                "rel": "featureinfo",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oas/v0/styles/ch.bafu.moose:wms:style?language=fr",
                                "rel": "styledby",
                                "title": "Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "properties": {
                            "type": "Distribution",
                            "title": "WMS Layer (FR)",
                            "description": "Description (FR)",
                            "protocol": "ogc:wms",
                            "externalIds": ["ch.bafu.moose"],
                        },
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=fr",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms.fr",
            "Body": {
                "id": "ch.bafu.moose:wms",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                        "rel": "alternate",
                        "title": "This Record (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                        "rel": "alternate",
                        "title": "This Record (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                        "rel": "alternate",
                        "title": "This Record (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=fr",
                        "rel": "dataset",
                        "title": "Link to parent dataset ch.bafu.moose",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=fr",
                        "rel": "dataservice",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                        "rel": "featureinfo",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oas/v0/styles/ch.bafu.moose:wms:style?language=fr",
                        "rel": "styledby",
                        "title": "Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "properties": {
                    "type": "Distribution",
                    "title": "WMS Layer (FR)",
                    "description": "Description (FR)",
                    "protocol": "ogc:wms",
                    "externalIds": ["ch.bafu.moose"],
                },
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-styles-static-dev-swissgeo",
            "Key": "api/oas/v0/styles/ch.bafu.moose:wms:style.fr",
            "Body": {
                "id": "ch.bafu.moose:wms:style",
                "layers": [
                    {
                        "id": "ch.bafu.moose:wms:style",
                        "paint": {"raster-opacity": 1.0, "raster-gutter": 0},
                        "source": "wmts-geoadminch",
                        "type": "raster",
                    }
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions.it",
            "Body": {
                "id": "ch.bafu.moose.distributions",
                "title": "Distribution Collection for ch.bafu.moose.distributions",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=it",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.it",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "ch.bafu.moose:wms",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                                "rel": "alternate",
                                "title": "This Record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                                "rel": "alternate",
                                "title": "This Record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                                "rel": "alternate",
                                "title": "This Record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=it",
                                "rel": "dataset",
                                "title": "Link to parent dataset ch.bafu.moose",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=it",
                                "rel": "dataservice",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                                "rel": "featureinfo",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oas/v0/styles/ch.bafu.moose:wms:style?language=it",
                                "rel": "styledby",
                                "title": "Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "properties": {
                            "type": "Distribution",
                            "title": "WMS Layer (IT)",
                            "description": "Description (IT)",
                            "protocol": "ogc:wms",
                            "externalIds": ["ch.bafu.moose"],
                        },
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=it",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms.it",
            "Body": {
                "id": "ch.bafu.moose:wms",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                        "rel": "alternate",
                        "title": "This Record (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                        "rel": "alternate",
                        "title": "This Record (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                        "rel": "alternate",
                        "title": "This Record (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=it",
                        "rel": "dataset",
                        "title": "Link to parent dataset ch.bafu.moose",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=it",
                        "rel": "dataservice",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                        "rel": "featureinfo",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oas/v0/styles/ch.bafu.moose:wms:style?language=it",
                        "rel": "styledby",
                        "title": "Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "properties": {
                    "type": "Distribution",
                    "title": "WMS Layer (IT)",
                    "description": "Description (IT)",
                    "protocol": "ogc:wms",
                    "externalIds": ["ch.bafu.moose"],
                },
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-styles-static-dev-swissgeo",
            "Key": "api/oas/v0/styles/ch.bafu.moose:wms:style.it",
            "Body": {
                "id": "ch.bafu.moose:wms:style",
                "layers": [
                    {
                        "id": "ch.bafu.moose:wms:style",
                        "paint": {"raster-opacity": 1.0, "raster-gutter": 0},
                        "source": "wmts-geoadminch",
                        "type": "raster",
                    }
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions.en",
            "Body": {
                "id": "ch.bafu.moose.distributions",
                "title": "Distribution Collection for ch.bafu.moose.distributions",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=en",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.en",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "ch.bafu.moose:wms",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                                "rel": "alternate",
                                "title": "This Record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                                "rel": "alternate",
                                "title": "This Record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                                "rel": "alternate",
                                "title": "This Record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=en",
                                "rel": "dataset",
                                "title": "Link to parent dataset ch.bafu.moose",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=en",
                                "rel": "dataservice",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                                "rel": "featureinfo",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oas/v0/styles/ch.bafu.moose:wms:style?language=en",
                                "rel": "styledby",
                                "title": "Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "properties": {
                            "type": "Distribution",
                            "title": "WMS Layer (EN)",
                            "description": "Description (EN)",
                            "protocol": "ogc:wms",
                            "externalIds": ["ch.bafu.moose"],
                        },
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=en",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms.en",
            "Body": {
                "id": "ch.bafu.moose:wms",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                        "rel": "alternate",
                        "title": "This Record (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                        "rel": "alternate",
                        "title": "This Record (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                        "rel": "alternate",
                        "title": "This Record (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=en",
                        "rel": "dataset",
                        "title": "Link to parent dataset ch.bafu.moose",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services/items/wmts-geoadminch?language=en",
                        "rel": "dataservice",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                        "rel": "featureinfo",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oas/v0/styles/ch.bafu.moose:wms:style?language=en",
                        "rel": "styledby",
                        "title": "Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "properties": {
                    "type": "Distribution",
                    "title": "WMS Layer (EN)",
                    "description": "Description (EN)",
                    "protocol": "ogc:wms",
                    "externalIds": ["ch.bafu.moose"],
                },
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-styles-static-dev-swissgeo",
            "Key": "api/oas/v0/styles/ch.bafu.moose:wms:style.en",
            "Body": {
                "id": "ch.bafu.moose:wms:style",
                "layers": [
                    {
                        "id": "ch.bafu.moose:wms:style",
                        "paint": {"raster-opacity": 1.0, "raster-gutter": 0},
                        "source": "wmts-geoadminch",
                        "type": "raster",
                    }
                ],
            },
            "ContentType": "application/json",
        },
    ]


@patch("dataset.management.commands.oar_export.Session")
def test_command_exports_geojson_distributions(session, db):
    dataservice = WMSDataservice(
        dataservice_id="wmts-geoadminch",
        title="WMTS geo.admin.ch",
        documentation_url_de="https://docs.geo.admin.ch/visualize-data/wmts.html",
        languages=["de", "fr", "en", "it"],
        capabilities_url="https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&FORMAT=text/xml&lang={lang}",
    )
    dataservice.save()

    dataset = Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="Rote Liste Moose (Gefährdung der Moose in der Schweiz)",
        title_short_fr="Liste rouge mousses",
        title_short_en="Red list bryophytes",
        title_short_it="Lista rossa delle biofite minacciate in Svizzera",
        title_short_rm="Glista cotschna dals mistgels (mistgels periclitads en Svizra)",
        description_de="missing",
        description_fr="missing",
        description_en="missing",
        description_it="missing",
        description_rm="missing",
        geocat_id="07b046a7-1b21-4cd0-b605-a113f2e5e94d",
    )
    dataset.save()

    ExternalGeoJSONDistribution(
        distribution_id="ch.bafu.moose:wms",
        dataset=dataset,
        title_de="GeoJSON Layer (DE)",
        title_fr="GeoJSON Layer (FR)",
        title_it="GeoJSON Layer (IT)",
        title_en="GeoJSON Layer (EN)",
        geojson_url_de="https://data.geo.admin.ch/ch.bafu.moose_de.json",
        geojson_url_fr="https://data.geo.admin.ch/ch.bafu.moose_fr.json",
        geojson_url_en="https://data.geo.admin.ch/ch.bafu.moose_en.json",
        geojson_url_it="https://data.geo.admin.ch/ch.bafu.moose_it.json",
        geojson_url_rm="https://data.geo.admin.ch/ch.bafu.moose_rm.json",
        style_url="https://api3.geo.admin.ch/static/vectorStyles/ch.bafu.moose.json",
    ).save()

    out = StringIO()
    call_command("oar_export", types=["distributions"], upload=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions.de" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.de" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions.fr" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.fr" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions.it" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.it" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions.en" in out
    assert "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.en" in out

    result = extract_put_object(session)
    assert result == [
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions.de",
            "Body": {
                "id": "ch.bafu.moose.distributions",
                "title": "Distribution Collection for ch.bafu.moose.distributions",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=de",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.de",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "ch.bafu.moose:wms",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                                "rel": "alternate",
                                "title": "This Record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                                "rel": "alternate",
                                "title": "This Record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                                "rel": "alternate",
                                "title": "This Record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=de",
                                "rel": "dataset",
                                "title": "Link to parent dataset ch.bafu.moose",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://data.geo.admin.ch/ch.bafu.moose_de.json",
                                "rel": "about",
                                "title": "Link to GeoJSON file",
                                "type": "application/geo+json",
                            },
                            {
                                "href": "https://api3.geo.admin.ch/static/vectorStyles/ch.bafu.moose.json",
                                "rel": "styled-by",
                                "title": "Link to style file for the GeoJSON layer",
                                "type": "application/json",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "properties": {
                            "type": "Distribution",
                            "title": "GeoJSON Layer (DE)",
                            "protocol": "geojson",
                        },
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=de",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms.de",
            "Body": {
                "id": "ch.bafu.moose:wms",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                        "rel": "alternate",
                        "title": "This Record (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                        "rel": "alternate",
                        "title": "This Record (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                        "rel": "alternate",
                        "title": "This Record (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=de",
                        "rel": "dataset",
                        "title": "Link to parent dataset ch.bafu.moose",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://data.geo.admin.ch/ch.bafu.moose_de.json",
                        "rel": "about",
                        "title": "Link to GeoJSON file",
                        "type": "application/geo+json",
                    },
                    {
                        "href": "https://api3.geo.admin.ch/static/vectorStyles/ch.bafu.moose.json",
                        "rel": "styled-by",
                        "title": "Link to style file for the GeoJSON layer",
                        "type": "application/json",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "properties": {
                    "type": "Distribution",
                    "title": "GeoJSON Layer (DE)",
                    "protocol": "geojson",
                },
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions.fr",
            "Body": {
                "id": "ch.bafu.moose.distributions",
                "title": "Distribution Collection for ch.bafu.moose.distributions",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=fr",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.fr",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "ch.bafu.moose:wms",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                                "rel": "alternate",
                                "title": "This Record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                                "rel": "alternate",
                                "title": "This Record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                                "rel": "alternate",
                                "title": "This Record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=fr",
                                "rel": "dataset",
                                "title": "Link to parent dataset ch.bafu.moose",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://data.geo.admin.ch/ch.bafu.moose_fr.json",
                                "rel": "about",
                                "title": "Link to GeoJSON file",
                                "type": "application/geo+json",
                            },
                            {
                                "href": "https://api3.geo.admin.ch/static/vectorStyles/ch.bafu.moose.json",
                                "rel": "styled-by",
                                "title": "Link to style file for the GeoJSON layer",
                                "type": "application/json",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "properties": {
                            "type": "Distribution",
                            "title": "GeoJSON Layer (FR)",
                            "protocol": "geojson",
                        },
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=fr",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms.fr",
            "Body": {
                "id": "ch.bafu.moose:wms",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                        "rel": "alternate",
                        "title": "This Record (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                        "rel": "alternate",
                        "title": "This Record (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                        "rel": "alternate",
                        "title": "This Record (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=fr",
                        "rel": "dataset",
                        "title": "Link to parent dataset ch.bafu.moose",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://data.geo.admin.ch/ch.bafu.moose_fr.json",
                        "rel": "about",
                        "title": "Link to GeoJSON file",
                        "type": "application/geo+json",
                    },
                    {
                        "href": "https://api3.geo.admin.ch/static/vectorStyles/ch.bafu.moose.json",
                        "rel": "styled-by",
                        "title": "Link to style file for the GeoJSON layer",
                        "type": "application/json",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "properties": {
                    "type": "Distribution",
                    "title": "GeoJSON Layer (FR)",
                    "protocol": "geojson",
                },
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions.it",
            "Body": {
                "id": "ch.bafu.moose.distributions",
                "title": "Distribution Collection for ch.bafu.moose.distributions",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=it",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.it",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "ch.bafu.moose:wms",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                                "rel": "alternate",
                                "title": "This Record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                                "rel": "alternate",
                                "title": "This Record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                                "rel": "alternate",
                                "title": "This Record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=it",
                                "rel": "dataset",
                                "title": "Link to parent dataset ch.bafu.moose",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://data.geo.admin.ch/ch.bafu.moose_it.json",
                                "rel": "about",
                                "title": "Link to GeoJSON file",
                                "type": "application/geo+json",
                            },
                            {
                                "href": "https://api3.geo.admin.ch/static/vectorStyles/ch.bafu.moose.json",
                                "rel": "styled-by",
                                "title": "Link to style file for the GeoJSON layer",
                                "type": "application/json",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "properties": {
                            "type": "Distribution",
                            "title": "GeoJSON Layer (IT)",
                            "protocol": "geojson",
                        },
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=it",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms.it",
            "Body": {
                "id": "ch.bafu.moose:wms",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                        "rel": "alternate",
                        "title": "This Record (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                        "rel": "alternate",
                        "title": "This Record (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                        "rel": "alternate",
                        "title": "This Record (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=it",
                        "rel": "dataset",
                        "title": "Link to parent dataset ch.bafu.moose",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://data.geo.admin.ch/ch.bafu.moose_it.json",
                        "rel": "about",
                        "title": "Link to GeoJSON file",
                        "type": "application/geo+json",
                    },
                    {
                        "href": "https://api3.geo.admin.ch/static/vectorStyles/ch.bafu.moose.json",
                        "rel": "styled-by",
                        "title": "Link to style file for the GeoJSON layer",
                        "type": "application/json",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "properties": {
                    "type": "Distribution",
                    "title": "GeoJSON Layer (IT)",
                    "protocol": "geojson",
                },
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions.en",
            "Body": {
                "id": "ch.bafu.moose.distributions",
                "title": "Distribution Collection for ch.bafu.moose.distributions",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=en",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items.en",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "ch.bafu.moose:wms",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                                "rel": "alternate",
                                "title": "This Record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                                "rel": "alternate",
                                "title": "This Record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                                "rel": "alternate",
                                "title": "This Record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=en",
                                "rel": "dataset",
                                "title": "Link to parent dataset ch.bafu.moose",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://data.geo.admin.ch/ch.bafu.moose_en.json",
                                "rel": "about",
                                "title": "Link to GeoJSON file",
                                "type": "application/geo+json",
                            },
                            {
                                "href": "https://api3.geo.admin.ch/static/vectorStyles/ch.bafu.moose.json",
                                "rel": "styled-by",
                                "title": "Link to style file for the GeoJSON layer",
                                "type": "application/json",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "properties": {
                            "type": "Distribution",
                            "title": "GeoJSON Layer (EN)",
                            "protocol": "geojson",
                        },
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=en",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms.en",
            "Body": {
                "id": "ch.bafu.moose:wms",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=en",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=de",
                        "rel": "alternate",
                        "title": "This Record (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=fr",
                        "rel": "alternate",
                        "title": "This Record (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items/ch.bafu.moose:wms?language=it",
                        "rel": "alternate",
                        "title": "This Record (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions?language=en",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=en",
                        "rel": "dataset",
                        "title": "Link to parent dataset ch.bafu.moose",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://data.geo.admin.ch/ch.bafu.moose_en.json",
                        "rel": "about",
                        "title": "Link to GeoJSON file",
                        "type": "application/geo+json",
                    },
                    {
                        "href": "https://api3.geo.admin.ch/static/vectorStyles/ch.bafu.moose.json",
                        "rel": "styled-by",
                        "title": "Link to style file for the GeoJSON layer",
                        "type": "application/json",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "properties": {
                    "type": "Distribution",
                    "title": "GeoJSON Layer (EN)",
                    "protocol": "geojson",
                },
            },
            "ContentType": "application/json",
        },
    ]


@patch("dataset.management.commands.oar_export.Session")
def test_command_exports_datasets(session, db):
    Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="Rote Liste Moose (Gefährdung der Moose in der Schweiz)",
        title_short_fr="Liste rouge mousses",
        title_short_en="Red list bryophytes",
        title_short_it="Lista rossa delle biofite minacciate in Svizzera",
        title_short_rm="Glista cotschna dals mistgels (mistgels periclitads en Svizra)",
        description_de="Description DE",
        description_fr="Description FR",
        description_en="Description EN",
        description_it="Description IT",
        description_rm="Description RM",
        geocat_id="07b046a7-1b21-4cd0-b605-a113f2e5e94d",
    ).save()

    out = StringIO()
    call_command("oar_export", types=["datasets"], upload=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "api/oar/staticv2/collections/swissgeo.catalog.de" in out
    assert "api/oar/staticv2/collections/swissgeo.catalog/items.de" in out
    assert "api/oar/staticv2/collections/swissgeo.catalog.fr" in out
    assert "api/oar/staticv2/collections/swissgeo.catalog/items.fr" in out
    assert "api/oar/staticv2/collections/swissgeo.catalog.it" in out
    assert "api/oar/staticv2/collections/swissgeo.catalog/items.it" in out
    assert "api/oar/staticv2/collections/swissgeo.catalog.en" in out
    assert "api/oar/staticv2/collections/swissgeo.catalog/items.en" in out

    result = extract_put_object(session)
    assert result == [
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/swissgeo.catalog.de",
            "Body": {
                "id": "swissgeo.catalog",
                "title": "Swissgeo Catalog",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=de",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=de",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/swissgeo.catalog/items.de",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "ch.bafu.moose",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=de",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=fr",
                                "rel": "alternate",
                                "title": "This Record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=it",
                                "rel": "alternate",
                                "title": "This Record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=en",
                                "rel": "alternate",
                                "title": "This Record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=de",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=de",
                                "rel": "distributions",
                                "title": "Distributions",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://www.geocat.ch/geonetwork/srv/ger/catalog.search#/metadata/07b046a7-1b21-4cd0-b605-a113f2e5e94d",
                                "rel": "alternate",
                                "title": "GeoCat Metadata",
                                "type": "text/html",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [5.96, 45.82],
                                    [5.96, 47.81],
                                    [10.49, 47.81],
                                    [10.49, 45.82],
                                    [5.96, 45.82],
                                ]
                            ],
                        },
                        "properties": {
                            "contacts": [],
                            "description": "Description DE",
                            "language": {
                                "code": "de",
                                "name": "Deutsch",
                                "dir": "ltr",
                                "alternate": "German",
                            },
                            "languages": [
                                {
                                    "code": "de",
                                    "name": "Deutsch",
                                    "dir": "ltr",
                                    "alternate": "German",
                                },
                                {
                                    "code": "fr",
                                    "name": "Français",
                                    "dir": "ltr",
                                    "alternate": "French",
                                },
                                {
                                    "code": "it",
                                    "name": "Italiano",
                                    "dir": "ltr",
                                    "alternate": "Italian",
                                },
                                {
                                    "code": "en",
                                    "name": "English",
                                    "dir": "ltr",
                                    "alternate": "English",
                                },
                            ],
                            "preferredDistributionId": None,
                            "title": "Rote Liste Moose (Gefährdung der Moose in der Schweiz)",
                            "type": "Dataset",
                        },
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=de",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=de",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose.de",
            "Body": {
                "id": "ch.bafu.moose",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=de",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=fr",
                        "rel": "alternate",
                        "title": "This Record (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=it",
                        "rel": "alternate",
                        "title": "This Record (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=en",
                        "rel": "alternate",
                        "title": "This Record (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=de",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=de",
                        "rel": "distributions",
                        "title": "Distributions",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://www.geocat.ch/geonetwork/srv/ger/catalog.search#/metadata/07b046a7-1b21-4cd0-b605-a113f2e5e94d",
                        "rel": "alternate",
                        "title": "GeoCat Metadata",
                        "type": "text/html",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [5.96, 45.82],
                            [5.96, 47.81],
                            [10.49, 47.81],
                            [10.49, 45.82],
                            [5.96, 45.82],
                        ]
                    ],
                },
                "properties": {
                    "contacts": [],
                    "description": "Description DE",
                    "language": {
                        "code": "de",
                        "name": "Deutsch",
                        "dir": "ltr",
                        "alternate": "German",
                    },
                    "languages": [
                        {"code": "de", "name": "Deutsch", "dir": "ltr", "alternate": "German"},
                        {"code": "fr", "name": "Français", "dir": "ltr", "alternate": "French"},
                        {"code": "it", "name": "Italiano", "dir": "ltr", "alternate": "Italian"},
                        {"code": "en", "name": "English", "dir": "ltr", "alternate": "English"},
                    ],
                    "preferredDistributionId": None,
                    "title": "Rote Liste Moose (Gefährdung der Moose in der Schweiz)",
                    "type": "Dataset",
                },
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/swissgeo.catalog.fr",
            "Body": {
                "id": "swissgeo.catalog",
                "title": "Swissgeo Catalog",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=fr",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=fr",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/swissgeo.catalog/items.fr",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "ch.bafu.moose",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=fr",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=de",
                                "rel": "alternate",
                                "title": "This Record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=it",
                                "rel": "alternate",
                                "title": "This Record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=en",
                                "rel": "alternate",
                                "title": "This Record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=fr",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=fr",
                                "rel": "distributions",
                                "title": "Distributions",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://www.geocat.ch/geonetwork/srv/fra/catalog.search#/metadata/07b046a7-1b21-4cd0-b605-a113f2e5e94d",
                                "rel": "alternate",
                                "title": "GeoCat Metadata",
                                "type": "text/html",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [5.96, 45.82],
                                    [5.96, 47.81],
                                    [10.49, 47.81],
                                    [10.49, 45.82],
                                    [5.96, 45.82],
                                ]
                            ],
                        },
                        "properties": {
                            "contacts": [],
                            "description": "Description FR",
                            "language": {
                                "code": "fr",
                                "name": "Français",
                                "dir": "ltr",
                                "alternate": "French",
                            },
                            "languages": [
                                {
                                    "code": "de",
                                    "name": "Deutsch",
                                    "dir": "ltr",
                                    "alternate": "German",
                                },
                                {
                                    "code": "fr",
                                    "name": "Français",
                                    "dir": "ltr",
                                    "alternate": "French",
                                },
                                {
                                    "code": "it",
                                    "name": "Italiano",
                                    "dir": "ltr",
                                    "alternate": "Italian",
                                },
                                {
                                    "code": "en",
                                    "name": "English",
                                    "dir": "ltr",
                                    "alternate": "English",
                                },
                            ],
                            "preferredDistributionId": None,
                            "title": "Liste rouge mousses",
                            "type": "Dataset",
                        },
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=fr",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=fr",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose.fr",
            "Body": {
                "id": "ch.bafu.moose",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=fr",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=de",
                        "rel": "alternate",
                        "title": "This Record (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=it",
                        "rel": "alternate",
                        "title": "This Record (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=en",
                        "rel": "alternate",
                        "title": "This Record (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=fr",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=fr",
                        "rel": "distributions",
                        "title": "Distributions",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://www.geocat.ch/geonetwork/srv/fra/catalog.search#/metadata/07b046a7-1b21-4cd0-b605-a113f2e5e94d",
                        "rel": "alternate",
                        "title": "GeoCat Metadata",
                        "type": "text/html",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [5.96, 45.82],
                            [5.96, 47.81],
                            [10.49, 47.81],
                            [10.49, 45.82],
                            [5.96, 45.82],
                        ]
                    ],
                },
                "properties": {
                    "contacts": [],
                    "description": "Description FR",
                    "language": {
                        "code": "fr",
                        "name": "Français",
                        "dir": "ltr",
                        "alternate": "French",
                    },
                    "languages": [
                        {"code": "de", "name": "Deutsch", "dir": "ltr", "alternate": "German"},
                        {"code": "fr", "name": "Français", "dir": "ltr", "alternate": "French"},
                        {"code": "it", "name": "Italiano", "dir": "ltr", "alternate": "Italian"},
                        {"code": "en", "name": "English", "dir": "ltr", "alternate": "English"},
                    ],
                    "preferredDistributionId": None,
                    "title": "Liste rouge mousses",
                    "type": "Dataset",
                },
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/swissgeo.catalog.it",
            "Body": {
                "id": "swissgeo.catalog",
                "title": "Swissgeo Catalog",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=it",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=it",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/swissgeo.catalog/items.it",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "ch.bafu.moose",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=it",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=de",
                                "rel": "alternate",
                                "title": "This Record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=fr",
                                "rel": "alternate",
                                "title": "This Record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=en",
                                "rel": "alternate",
                                "title": "This Record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=it",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=it",
                                "rel": "distributions",
                                "title": "Distributions",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://www.geocat.ch/geonetwork/srv/ita/catalog.search#/metadata/07b046a7-1b21-4cd0-b605-a113f2e5e94d",
                                "rel": "alternate",
                                "title": "GeoCat Metadata",
                                "type": "text/html",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [5.96, 45.82],
                                    [5.96, 47.81],
                                    [10.49, 47.81],
                                    [10.49, 45.82],
                                    [5.96, 45.82],
                                ]
                            ],
                        },
                        "properties": {
                            "contacts": [],
                            "description": "Description IT",
                            "language": {
                                "code": "it",
                                "name": "Italiano",
                                "dir": "ltr",
                                "alternate": "Italian",
                            },
                            "languages": [
                                {
                                    "code": "de",
                                    "name": "Deutsch",
                                    "dir": "ltr",
                                    "alternate": "German",
                                },
                                {
                                    "code": "fr",
                                    "name": "Français",
                                    "dir": "ltr",
                                    "alternate": "French",
                                },
                                {
                                    "code": "it",
                                    "name": "Italiano",
                                    "dir": "ltr",
                                    "alternate": "Italian",
                                },
                                {
                                    "code": "en",
                                    "name": "English",
                                    "dir": "ltr",
                                    "alternate": "English",
                                },
                            ],
                            "preferredDistributionId": None,
                            "title": "Lista rossa delle biofite minacciate in Svizzera",
                            "type": "Dataset",
                        },
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=it",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=en",
                        "rel": "alternate",
                        "title": "Link to this resource (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=it",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose.it",
            "Body": {
                "id": "ch.bafu.moose",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=it",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=de",
                        "rel": "alternate",
                        "title": "This Record (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=fr",
                        "rel": "alternate",
                        "title": "This Record (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=en",
                        "rel": "alternate",
                        "title": "This Record (English)",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=it",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=it",
                        "rel": "distributions",
                        "title": "Distributions",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://www.geocat.ch/geonetwork/srv/ita/catalog.search#/metadata/07b046a7-1b21-4cd0-b605-a113f2e5e94d",
                        "rel": "alternate",
                        "title": "GeoCat Metadata",
                        "type": "text/html",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [5.96, 45.82],
                            [5.96, 47.81],
                            [10.49, 47.81],
                            [10.49, 45.82],
                            [5.96, 45.82],
                        ]
                    ],
                },
                "properties": {
                    "contacts": [],
                    "description": "Description IT",
                    "language": {
                        "code": "it",
                        "name": "Italiano",
                        "dir": "ltr",
                        "alternate": "Italian",
                    },
                    "languages": [
                        {"code": "de", "name": "Deutsch", "dir": "ltr", "alternate": "German"},
                        {"code": "fr", "name": "Français", "dir": "ltr", "alternate": "French"},
                        {"code": "it", "name": "Italiano", "dir": "ltr", "alternate": "Italian"},
                        {"code": "en", "name": "English", "dir": "ltr", "alternate": "English"},
                    ],
                    "preferredDistributionId": None,
                    "title": "Lista rossa delle biofite minacciate in Svizzera",
                    "type": "Dataset",
                },
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/swissgeo.catalog.en",
            "Body": {
                "id": "swissgeo.catalog",
                "title": "Swissgeo Catalog",
                "type": "Collection",
                "itemType": "record",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=en",
                        "rel": "items",
                        "title": "Link to the items of this collection",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=en",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/swissgeo.catalog/items.en",
            "Body": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "ch.bafu.moose",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=en",
                                "rel": "self",
                                "title": "This Record",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=de",
                                "rel": "alternate",
                                "title": "This Record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=fr",
                                "rel": "alternate",
                                "title": "This Record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=it",
                                "rel": "alternate",
                                "title": "This Record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=en",
                                "rel": "collection",
                                "title": "Link to the collection this item belongs to",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=en",
                                "rel": "distributions",
                                "title": "Distributions",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://www.geocat.ch/geonetwork/srv/eng/catalog.search#/metadata/07b046a7-1b21-4cd0-b605-a113f2e5e94d",
                                "rel": "alternate",
                                "title": "GeoCat Metadata",
                                "type": "text/html",
                            },
                        ],
                        "linkTemplates": [],
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [5.96, 45.82],
                                    [5.96, 47.81],
                                    [10.49, 47.81],
                                    [10.49, 45.82],
                                    [5.96, 45.82],
                                ]
                            ],
                        },
                        "properties": {
                            "contacts": [],
                            "description": "Description EN",
                            "language": {
                                "code": "en",
                                "name": "English",
                                "dir": "ltr",
                                "alternate": "English",
                            },
                            "languages": [
                                {
                                    "code": "de",
                                    "name": "Deutsch",
                                    "dir": "ltr",
                                    "alternate": "German",
                                },
                                {
                                    "code": "fr",
                                    "name": "Français",
                                    "dir": "ltr",
                                    "alternate": "French",
                                },
                                {
                                    "code": "it",
                                    "name": "Italiano",
                                    "dir": "ltr",
                                    "alternate": "Italian",
                                },
                                {
                                    "code": "en",
                                    "name": "English",
                                    "dir": "ltr",
                                    "alternate": "English",
                                },
                            ],
                            "preferredDistributionId": None,
                            "title": "Red list bryophytes",
                            "type": "Dataset",
                        },
                    }
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=en",
                        "rel": "self",
                        "title": "Link to this resource",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=de",
                        "rel": "alternate",
                        "title": "Link to this resource (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=fr",
                        "rel": "alternate",
                        "title": "Link to this resource (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=it",
                        "rel": "alternate",
                        "title": "Link to this resource (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=en",
                        "rel": "collection",
                        "title": "Link to the collection these items belong to",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose.en",
            "Body": {
                "id": "ch.bafu.moose",
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=en",
                        "rel": "self",
                        "title": "This Record",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=de",
                        "rel": "alternate",
                        "title": "This Record (German)",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=fr",
                        "rel": "alternate",
                        "title": "This Record (French)",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items/ch.bafu.moose?language=it",
                        "rel": "alternate",
                        "title": "This Record (Italian)",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=en",
                        "rel": "collection",
                        "title": "Link to the collection this item belongs to",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/ch.bafu.moose.distributions/items?language=en",
                        "rel": "distributions",
                        "title": "Distributions",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://www.geocat.ch/geonetwork/srv/eng/catalog.search#/metadata/07b046a7-1b21-4cd0-b605-a113f2e5e94d",
                        "rel": "alternate",
                        "title": "GeoCat Metadata",
                        "type": "text/html",
                    },
                ],
                "linkTemplates": [],
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [5.96, 45.82],
                            [5.96, 47.81],
                            [10.49, 47.81],
                            [10.49, 45.82],
                            [5.96, 45.82],
                        ]
                    ],
                },
                "properties": {
                    "contacts": [],
                    "description": "Description EN",
                    "language": {
                        "code": "en",
                        "name": "English",
                        "dir": "ltr",
                        "alternate": "English",
                    },
                    "languages": [
                        {"code": "de", "name": "Deutsch", "dir": "ltr", "alternate": "German"},
                        {"code": "fr", "name": "Français", "dir": "ltr", "alternate": "French"},
                        {"code": "it", "name": "Italiano", "dir": "ltr", "alternate": "Italian"},
                        {"code": "en", "name": "English", "dir": "ltr", "alternate": "English"},
                    ],
                    "preferredDistributionId": None,
                    "title": "Red list bryophytes",
                    "type": "Dataset",
                },
            },
            "ContentType": "application/json",
        },
    ]


@patch("dataset.management.commands.oar_export.Session")
def test_command_exports_landingpage(session, db):
    out = StringIO()
    call_command("oar_export", types=["landing_page"], upload=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "api/oar/staticv2/landingpage" in out
    assert "api/oar/staticv2/conformance.de" in out
    assert "api/oar/staticv2/conformance.fr" in out
    assert "api/oar/staticv2/conformance.it" in out
    assert "api/oar/staticv2/conformance.en" in out
    assert "api/oar/staticv2/collections.de" in out
    assert "api/oar/staticv2/collections.fr" in out
    assert "api/oar/staticv2/collections.it" in out
    assert "api/oar/staticv2/collections.en" in out

    result = extract_put_object(session)
    assert result == [
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/landingpage",
            "Body": {
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
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections",
                        "rel": "data",
                        "type": "application/json",
                        "title": "Swissgeo Catalog Collection",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/conformance",
                        "rel": "conformance",
                        "type": "application/json",
                        "title": "Conformance Declaration",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/conformance.de",
            "Body": {
                "conformsTo": [
                    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core",
                    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/collections",
                    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/json",
                ]
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/conformance.fr",
            "Body": {
                "conformsTo": [
                    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core",
                    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/collections",
                    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/json",
                ]
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/conformance.it",
            "Body": {
                "conformsTo": [
                    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core",
                    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/collections",
                    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/json",
                ]
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/conformance.en",
            "Body": {
                "conformsTo": [
                    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core",
                    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/collections",
                    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/json",
                ]
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections.de",
            "Body": {
                "collections": [
                    {
                        "id": "swissgeo.catalog",
                        "title": "Swissgeo Catalog",
                        "description": "Collection of all swissgeo datasets",
                        "itemType": "record",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=de",
                                "rel": "self",
                                "title": "This record",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=fr",
                                "rel": "alternate",
                                "title": "This record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=it",
                                "rel": "alternate",
                                "title": "This record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=en",
                                "rel": "alternate",
                                "title": "This record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=de",
                                "rel": "items",
                                "type": "application/json",
                                "hreflang": "de",
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
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=de",
                                "rel": "self",
                                "title": "This record",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=fr",
                                "rel": "alternate",
                                "title": "This record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=it",
                                "rel": "alternate",
                                "title": "This record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=en",
                                "rel": "alternate",
                                "title": "This record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                        ],
                    },
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=de",
                        "rel": "self",
                        "description": "This document",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=fr",
                        "rel": "alternate",
                        "description": "This document French",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=it",
                        "rel": "alternate",
                        "description": "This document Italian",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=en",
                        "rel": "alternate",
                        "description": "This document English",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections.fr",
            "Body": {
                "collections": [
                    {
                        "id": "swissgeo.catalog",
                        "title": "Swissgeo Catalog",
                        "description": "Collection of all swissgeo datasets",
                        "itemType": "record",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=fr",
                                "rel": "self",
                                "title": "This record",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=de",
                                "rel": "alternate",
                                "title": "This record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=it",
                                "rel": "alternate",
                                "title": "This record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=en",
                                "rel": "alternate",
                                "title": "This record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=fr",
                                "rel": "items",
                                "type": "application/json",
                                "hreflang": "fr",
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
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=fr",
                                "rel": "self",
                                "title": "This record",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=de",
                                "rel": "alternate",
                                "title": "This record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=it",
                                "rel": "alternate",
                                "title": "This record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=en",
                                "rel": "alternate",
                                "title": "This record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                        ],
                    },
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=fr",
                        "rel": "self",
                        "description": "This document",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=de",
                        "rel": "alternate",
                        "description": "This document German",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=it",
                        "rel": "alternate",
                        "description": "This document Italian",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=en",
                        "rel": "alternate",
                        "description": "This document English",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections.it",
            "Body": {
                "collections": [
                    {
                        "id": "swissgeo.catalog",
                        "title": "Swissgeo Catalog",
                        "description": "Collection of all swissgeo datasets",
                        "itemType": "record",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=it",
                                "rel": "self",
                                "title": "This record",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=de",
                                "rel": "alternate",
                                "title": "This record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=fr",
                                "rel": "alternate",
                                "title": "This record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=en",
                                "rel": "alternate",
                                "title": "This record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=it",
                                "rel": "items",
                                "type": "application/json",
                                "hreflang": "it",
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
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=it",
                                "rel": "self",
                                "title": "This record",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=de",
                                "rel": "alternate",
                                "title": "This record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=fr",
                                "rel": "alternate",
                                "title": "This record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=en",
                                "rel": "alternate",
                                "title": "This record (English)",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                        ],
                    },
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=it",
                        "rel": "self",
                        "description": "This document",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=de",
                        "rel": "alternate",
                        "description": "This document German",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=fr",
                        "rel": "alternate",
                        "description": "This document French",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=en",
                        "rel": "alternate",
                        "description": "This document English",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                ],
            },
            "ContentType": "application/json",
        },
        {
            "Bucket": "oa-records-static-v2-dev-swissgeo",
            "Key": "api/oar/staticv2/collections.en",
            "Body": {
                "collections": [
                    {
                        "id": "swissgeo.catalog",
                        "title": "Swissgeo Catalog",
                        "description": "Collection of all swissgeo datasets",
                        "itemType": "record",
                        "links": [
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=en",
                                "rel": "self",
                                "title": "This record",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=de",
                                "rel": "alternate",
                                "title": "This record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=fr",
                                "rel": "alternate",
                                "title": "This record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog?language=it",
                                "rel": "alternate",
                                "title": "This record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/swissgeo.catalog/items?language=en",
                                "rel": "items",
                                "type": "application/json",
                                "hreflang": "en",
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
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=en",
                                "rel": "self",
                                "title": "This record",
                                "type": "application/json",
                                "hreflang": "en",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=de",
                                "rel": "alternate",
                                "title": "This record (German)",
                                "type": "application/json",
                                "hreflang": "de",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=fr",
                                "rel": "alternate",
                                "title": "This record (French)",
                                "type": "application/json",
                                "hreflang": "fr",
                            },
                            {
                                "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections/geoadmin.services?language=it",
                                "rel": "alternate",
                                "title": "This record (Italian)",
                                "type": "application/json",
                                "hreflang": "it",
                            },
                        ],
                    },
                ],
                "links": [
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=en",
                        "rel": "self",
                        "description": "This document",
                        "type": "application/json",
                        "hreflang": "en",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=de",
                        "rel": "alternate",
                        "description": "This document German",
                        "type": "application/json",
                        "hreflang": "de",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=fr",
                        "rel": "alternate",
                        "description": "This document French",
                        "type": "application/json",
                        "hreflang": "fr",
                    },
                    {
                        "href": "https://services.dev.sgdi.tech/api/oar/staticv2/collections?language=it",
                        "rel": "alternate",
                        "description": "This document Italian",
                        "type": "application/json",
                        "hreflang": "it",
                    },
                ],
            },
            "ContentType": "application/json",
        },
    ]
