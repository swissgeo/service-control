from django.urls import reverse

import pytest

from dataservice.models import (
    GeoadminFeaturesDataservice,
    OGCAPIFeaturesDataservice,
    OGCAPIStacDataservice,
    WFSDataservice,
    WMSDataservice,
    WMTSDataservice,
)
from dataset.models import Dataset
from distribution.models import (
    ExternalGeoadminFeaturesDistribution,
    ExternalGeoJSONDistribution,
    ExternalStacDistribution,
    ExternalWMSDistribution,
    ExternalWMTSDistribution,
)
from organization.models import Attribution, Contact
from tests.admin.test_dataset_admin import ADMIN_HEADERS
from thesaurus.models import Concept, Thesaurus

ADMIN_MODELS = (
    "dataset_dataset",
    "distribution_externalwmsdistribution",
    "distribution_externalwmtsdistribution",
    "distribution_externalstacdistribution",
    "distribution_externalgeojsondistribution",
    "distribution_externalgeoadminfeaturesdistribution",
    "organization_organization",
    "organization_unit",
    "organization_contact",
    "organization_attribution",
    "dataservice_wmsdataservice",
    "dataservice_wmtsdataservice",
    "dataservice_wfsdataservice",
    "dataservice_ogcapifeaturesdataservice",
    "dataservice_ogcapistacdataservice",
    "dataservice_geoadminfeaturesdataservice",
    "thesaurus_thesaurus",
    "thesaurus_concept",
)


@pytest.fixture(name="admin_objects")
def fixture_admin_objects(organization, unit):
    thesaurus = Thesaurus.objects.create(thesaurus_id="thesaurus")
    dataset = Dataset.objects.create(
        sgid="dat_test",
        dataset_id="dataset.test",
        title_de="Title (DE)",
        title_fr="Title (FR)",
        title_en="Title (EN)",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
    )
    common = {"dataset": dataset, "title_de": "Title", "data_source": "user-input"}
    return {
        "dataset_dataset": dataset,
        "distribution_externalwmsdistribution": ExternalWMSDistribution.objects.create(
            sgid="dst_wms", distribution_id="dst.wms", wms_layer_name_de="wms", **common
        ),
        "distribution_externalwmtsdistribution": ExternalWMTSDistribution.objects.create(
            sgid="dst_wmts", distribution_id="dst.wmts", wmts_layer_name_de="wmts", **common
        ),
        "distribution_externalstacdistribution": ExternalStacDistribution.objects.create(
            sgid="dst_stac", distribution_id="dst.stac", stac_collection_id="stac", **common
        ),
        "distribution_externalgeojsondistribution": ExternalGeoJSONDistribution.objects.create(
            sgid="dst_geojson",
            distribution_id="dst.geojson",
            geojson_url_de="https://example.com/de.json",
            **common,
        ),
        "distribution_externalgeoadminfeaturesdistribution": (
            ExternalGeoadminFeaturesDistribution.objects.create(
                sgid="dst_features", distribution_id="dst.features", layer_id="layer", **common
            )
        ),
        "organization_organization": organization,
        "organization_unit": unit,
        "organization_contact": Contact.objects.create(organization=organization, name_de="Name"),
        "organization_attribution": Attribution.objects.create(
            attribution_id="ch.bafu",
            organization=organization,
            abbreviation_de="BAFU",
            abbreviation_fr="OFEV",
            abbreviation_en="FOEN",
            name_de="Name",
            name_fr="Name",
            name_en="Name",
        ),
        "dataservice_wmsdataservice": WMSDataservice.objects.create(
            title="WMS", capabilities_url="https://example.com/wms"
        ),
        "dataservice_wmtsdataservice": WMTSDataservice.objects.create(
            title="WMTS", capabilities_url="https://example.com/wmts", variable_epsg_list=[2056]
        ),
        "dataservice_wfsdataservice": WFSDataservice.objects.create(title="WFS"),
        "dataservice_ogcapifeaturesdataservice": OGCAPIFeaturesDataservice.objects.create(
            title="OGC API Features"
        ),
        "dataservice_ogcapistacdataservice": OGCAPIStacDataservice.objects.create(
            title="STAC", landing_page_url="https://example.com/stac"
        ),
        "dataservice_geoadminfeaturesdataservice": GeoadminFeaturesDataservice.objects.create(
            title="Geoadmin Features"
        ),
        "thesaurus_thesaurus": thesaurus,
        "thesaurus_concept": Concept.objects.create(
            thesaurus=thesaurus,
            concept_id="concept",
            label_de="Label",
            label_fr="Label",
            label_en="Label",
        ),
    }


@pytest.mark.parametrize("model", ADMIN_MODELS)
def test_admin_add_form_renders(client, db, model):
    response = client.get(reverse(f"admin:{model}_add"), **ADMIN_HEADERS)

    assert response.status_code == 200
    assert "Identification" in response.text
    assert "Metadata" not in response.text


@pytest.mark.parametrize("model", ADMIN_MODELS)
def test_admin_change_form_renders(client, admin_objects, model):
    obj = admin_objects[model]

    response = client.get(reverse(f"admin:{model}_change", args=[obj.pk]), **ADMIN_HEADERS)

    assert response.status_code == 200
    assert "Identification" in response.text
    assert "Metadata" in response.text
