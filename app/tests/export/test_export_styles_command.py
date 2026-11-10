import json
from io import StringIO
from json import loads
from pathlib import Path
from unittest.mock import patch

from django.apps import apps
from django.core.management import call_command

import pytest

from dataset.models import Dataset
from distribution.models import (
    ExternalGeoJSONDistribution,
    ExternalWMSDistribution,
    ExternalWMTSDistribution,
)
from export.export_models import OARDistribution


def extract_put_object(session):
    result = []
    for call in session.mock_calls:
        if "put_object" in str(call):
            kwargs = call.kwargs.copy()
            kwargs["Body"] = loads(kwargs["Body"])
            result.append(kwargs)
    return result


def extract_delete_objects(session):
    return [call.kwargs for call in session.mock_calls if "delete_objects" in str(call)]


@patch("export.management.commands.export_styles.Session")
def test_command_exports_wms_styles(session, db):
    dataset = Dataset(
        sgid="dat_moose",
        dataset_id="ch.bafu.moose",
        title_de="Rote Liste Moose (Gefährdung der Moose in der Schweiz)",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        description_de="missing",
        description_fr="missing",
        description_en="missing",
    )
    dataset.save()

    ExternalWMSDistribution(
        sgid="dst_moose-123",
        distribution_id="ch.bafu.moose:wms",
        dataset=dataset,
        opacity=0.5,
        gutter=1,
    ).save()

    out = StringIO()
    call_command("export_styles", wms=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "api/oas/v0/styles/sty_moose-123" in out

    result = extract_put_object(session)
    assert result == [
        {
            "Bucket": "oa-styles-static-dev-swissgeo",
            "Key": "api/oas/v0/styles/sty_moose-123",
            "Body": {
                "layers": [
                    {
                        "id": "dst_moose-123",
                        "source": "wms.geo.admin.ch",
                        "type": "raster",
                        "paint": {"raster-opacity": 0.5, "raster-gutter": 1},
                    }
                ]
            },
            "ContentType": "application/json",
        }
    ]


@patch("export.management.commands.export_styles.Session")
def test_command_exports_wmts_styles(session, db):
    dataset = Dataset(
        sgid="dat_moose",
        dataset_id="ch.bafu.moose",
        title_de="Rote Liste Moose (Gefährdung der Moose in der Schweiz)",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        description_de="missing",
        description_fr="missing",
        description_en="missing",
    )
    dataset.save()

    ExternalWMTSDistribution(
        sgid="dst_moose-123",
        distribution_id="dst_moose-123",
        dataset=dataset,
        opacity=0.5,
    ).save()

    out = StringIO()
    call_command("export_styles", wmts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "api/oas/v0/styles/sty_moose-123" in out

    result = extract_put_object(session)
    assert result == [
        {
            "Bucket": "oa-styles-static-dev-swissgeo",
            "Key": "api/oas/v0/styles/sty_moose-123",
            "Body": {
                "layers": [
                    {
                        "id": "dst_moose-123",
                        "source": "wmts.geo.admin.ch",
                        "type": "raster",
                        "paint": {"raster-opacity": 0.5},
                    }
                ]
            },
            "ContentType": "application/json",
        }
    ]


@patch("export.management.commands.export_styles.Session")
def test_command_exports_geojson_styles(session, db):
    path = (
        Path(apps.get_app_config("distribution").path)
        / "styles"
        / "ch.bfe.shared-mobility.maplibre.json"
    )
    with open(path) as file:
        style = json.load(file)

    dataset = Dataset(
        sgid="dat_moose",
        dataset_id="ch.bafu.moose",
        title_de="Rote Liste Moose (Gefährdung der Moose in der Schweiz)",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        description_de="missing",
        description_fr="missing",
        description_en="missing",
    )
    dataset.save()

    ExternalGeoJSONDistribution(
        sgid="dst_moose-123",
        distribution_id="ch.bafu.moose:geojson",
        dataset=dataset,
        style_url="/api/oas/v0/styles/ch.bfe.shared-mobility.maplibre.json",
    ).save()

    out = StringIO()
    call_command("export_styles", geojson=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "api/oas/v0/styles/ch.bfe.shared-mobility.maplibre.json" in out

    result = extract_put_object(session)
    assert result == [
        {
            "Bucket": "oa-styles-static-dev-swissgeo",
            "Key": "api/oas/v0/styles/ch.bfe.shared-mobility.maplibre.json",
            "Body": style,
            "ContentType": "application/json",
        }
    ]


@patch("export.management.commands.export_styles.Session")
def test_command_exports_styles_dry(session, db):
    dataset = Dataset(
        sgid="dat_moose",
        dataset_id="ch.bafu.moose",
        title_de="Rote Liste Moose (Gefährdung der Moose in der Schweiz)",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        description_de="missing",
        description_fr="missing",
        description_en="missing",
    )
    dataset.save()

    ExternalWMSDistribution(
        sgid="dst_moose-123",
        distribution_id="ch.bafu.moose:wms",
        dataset=dataset,
        opacity=0.5,
        gutter=1,
    ).save()

    out = StringIO()
    call_command("export_styles", wms=True, dry_run=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "api/oas/v0/styles/sty_moose-123" in out
    assert "DRY RUN" in out

    result = extract_put_object(session)
    assert result == []


@patch("export.management.commands.export_styles.Session")
def test_command_cleans_styles(session, db):
    dataset = Dataset(
        sgid="dat_moose",
        dataset_id="ch.bafu.moose",
        title_de="Rote Liste Moose (Gefährdung der Moose in der Schweiz)",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        description_de="missing",
        description_fr="missing",
        description_en="missing",
    )
    dataset.save()

    ExternalWMSDistribution(
        sgid="dst_moose-123",
        distribution_id="ch.bafu.moose:wms",
        dataset=dataset,
        opacity=0.5,
        gutter=1,
    ).save()

    s3 = session.return_value.client.return_value
    s3.list_objects_v2.side_effect = [
        {"Contents": [{"Key": "a"}], "NextContinuationToken": "tok"},
        {"Contents": [{"Key": "b"}]},
    ]

    out = StringIO()
    call_command(
        "export_styles",
        # "--target-env", "local",
        "--verbosity",
        "2",
        "clean",
        stdout=out,
    )
    out = out.getvalue()

    assert "Deleted total of 2 objects" in out

    result = extract_delete_objects(session)
    assert result == [
        {"Bucket": "oa-styles-static-dev-swissgeo", "Delete": {"Objects": [{"Key": "a"}]}},
        {"Bucket": "oa-styles-static-dev-swissgeo", "Delete": {"Objects": [{"Key": "b"}]}},
    ]


@pytest.mark.parametrize(
    ("distribution_cls", "distribution_kwargs", "export_flag"),
    [
        (
            ExternalWMSDistribution,
            {"distribution_id": "ch.bafu.moose:wms", "opacity": 0.5, "gutter": 1},
            "wms",
        ),
        (
            ExternalWMTSDistribution,
            {"distribution_id": "ch.bafu.moose:wmts", "opacity": 0.5},
            "wmts",
        ),
        (
            ExternalGeoJSONDistribution,
            {
                "distribution_id": "ch.bafu.moose:geojson",
                "geojson_url_de": "https://data.geo.admin.ch/ch.bafu.moose.geojson",
                "style_url": "/api/oas/v0/styles/ch.bfe.shared-mobility.maplibre.json",
            },
            "geojson",
        ),
    ],
    ids=["wms", "wmts", "geojson"],
)
@patch("export.management.commands.export_styles.Session")
def test_exported_style_key_matches_distribution_style_link(
    session, db, distribution_cls, distribution_kwargs, export_flag
):
    """The style uploaded by `export_styles` must be reachable via the `styledBy` link of the
    exported OAR distribution record."""
    dataset = Dataset(
        sgid="dat_moose",
        dataset_id="ch.bafu.moose",
        title_de="Rote Liste Moose (Gefährdung der Moose in der Schweiz)",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        description_de="missing",
        description_fr="missing",
        description_en="missing",
    )
    dataset.save()

    distribution = distribution_cls(sgid="dst_moose-123", dataset=dataset, **distribution_kwargs)
    distribution.save()

    record = OARDistribution.from_distribution(distribution, "de")
    style_links = [link.href for link in record.links if link.rel == "styledBy"]
    assert len(style_links) == 1

    call_command("export_styles", **{export_flag: True}, verbosity=0, stdout=StringIO())

    result = extract_put_object(session)
    assert len(result) == 1
    # Links are relative to the host, S3 keys have no leading slash
    assert f"/{result[0]['Key']}" == style_links[0]
