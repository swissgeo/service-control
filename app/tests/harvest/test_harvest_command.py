from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command

import pytest

from dataset.models import Dataset, DatasetToContact, DatasetToUnit
from harvest.import_models import (
    Contact,
    ContactList,
    DatasetImport,
    Keyword,
    KeywordList,
    OnlineResource,
    OrganizationImport,
)
from harvest.models import (
    DatasetMapping,
    DatasetToContactMapping,
    DatasetToUnitMapping,
    OrganizationMapping,
)
from organization.models import Contact as ContactModel
from organization.models import Organization, Unit
from thesaurus.models import Keyword as KeywordModel
from thesaurus.models import Thesaurus


@pytest.fixture(name="dynamodb")
def fixture_dynamodb():
    """Mocks the boto3 session used for paginated DynamoDB access.

    Returns the client.

    Use it with pagination like this:

        def test_foo(dynamodb):
            dynamodb.get_paginator().paginate.return_value = [
                {"Items": [{"foo": 1}]},
                {"Items": [{"foo": 2}]},
            ]

    Use it with get item like this:

        def test_bar(dynamodb):
            dynamodb.get_item.return_value = {"Item": {"bar": 1}}

    """

    with patch("harvest.management.commands.import_harvest_tables.Session") as mock_session_cls:
        paginator = MagicMock()
        client = MagicMock()
        client.get_paginator.return_value = paginator
        session = MagicMock()
        session.client.return_value = client
        mock_session_cls.return_value = session
        yield client


# --------------------------------------------------------------------------------------------------
# Organizations
# --------------------------------------------------------------------------------------------------


@patch("organization.models.Client")
def test_command_creates_organizations(client, dynamodb, db):
    org_in = OrganizationImport(
        provider_id="ch.bafu",
        name_de="Bundesamt für Umwelt",
        name_fr="Office fédéral de l'environnement",
        name_en="Federal Office for the Environment",
        name_it="Ufficio federale dell'ambiente",
        name_rm="Uffizi federal per l'ambient",
        acronym_de="BAFU",
        acronym_fr="OFEV",
        acronym_en="FOEN",
        acronym_it="UFAM",
        acronym_rm="UFAM",
    )

    dynamodb.get_paginator().paginate.return_value = [{"Items": [org_in.as_dynamodb_item()]}]

    out = StringIO()
    call_command("import_harvest_tables", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with provider_id ch.bafu does not exist yet, creating a new one" in out

    org_out = Organization.objects.first()
    assert org_out
    assert org_out.organization_id == "ch.bafu"
    assert org_out.name_de == "Bundesamt für Umwelt"
    assert org_out.name_fr == "Office fédéral de l'environnement"
    assert org_out.name_en == "Federal Office for the Environment"
    assert org_out.name_it == "Ufficio federale dell'ambiente"
    assert org_out.name_rm == "Uffizi federal per l'ambient"
    assert org_out.acronym_de == "BAFU"
    assert org_out.acronym_fr == "OFEV"
    assert org_out.acronym_en == "FOEN"
    assert org_out.acronym_it == "UFAM"
    assert org_out.acronym_rm == "UFAM"
    assert org_out.data_source == Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION
    assert org_out.data_source_ids == ["ch.bafu"]


@patch("organization.models.Client")
def test_command_updates_organizations(client, dynamodb, db):
    Organization(
        organization_id="ch.bafu",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION,
        data_source_ids=[],
    ).save()

    org_in = OrganizationImport(
        provider_id="ch.bafu",
        name_de="Bundesamt für Umwelt",
        name_fr="Office fédéral de l'environnement",
        name_en="Federal Office for the Environment",
        name_it="Ufficio federale dell'ambiente",
        name_rm="Uffizi federal per l'ambient",
        acronym_de="BAFU",
        acronym_fr="OFEV",
        acronym_en="FOEN",
        acronym_it="UFAM",
        acronym_rm="UFAM",
    )

    dynamodb.get_paginator().paginate.return_value = [{"Items": [org_in.as_dynamodb_item()]}]

    out = StringIO()
    call_command("import_harvest_tables", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Organization with provider_id ch.bafu already exists" in out

    org_out = Organization.objects.first()
    assert org_out
    assert org_out.organization_id == "ch.bafu"
    assert org_out.name_de == "Bundesamt für Umwelt"
    assert org_out.name_fr == "Office fédéral de l'environnement"
    assert org_out.name_en == "Federal Office for the Environment"
    assert org_out.name_it == "Ufficio federale dell'ambiente"
    assert org_out.name_rm == "Uffizi federal per l'ambient"
    assert org_out.acronym_de == "BAFU"
    assert org_out.acronym_fr == "OFEV"
    assert org_out.acronym_en == "FOEN"
    assert org_out.acronym_it == "UFAM"
    assert org_out.acronym_rm == "UFAM"
    assert org_out.data_source == Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION
    assert org_out.data_source_ids == ["ch.bafu"]


@patch("organization.models.Client")
def test_command_uses_one_to_one_organization_mapping(client, dynamodb, db):
    org_1 = Organization(
        organization_id="ch.bafu1",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION,
        data_source_ids=["ch.bafu"],
    )
    org_1.save()
    org_2 = Organization(
        organization_id="ch.bafu2",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION,
        data_source_ids=["ch.bafu"],
    )
    org_2.save()

    org_in = OrganizationImport(
        provider_id="ch.bafu",
        name_de="Bundesamt für Umwelt",
        name_fr="Office fédéral de l'environnement",
        name_en="Federal Office for the Environment",
        name_it="Ufficio federale dell'ambiente",
        name_rm="Uffizi federal per l'ambient",
        acronym_de="BAFU",
        acronym_fr="OFEV",
        acronym_en="FOEN",
        acronym_it="UFAM",
        acronym_rm="UFAM",
    )

    OrganizationMapping(
        provider_id_prefix="ch.bafu", organization_id="ch.bafu1", update_organization=True
    ).save()

    dynamodb.get_paginator().paginate.return_value = [{"Items": [org_in.as_dynamodb_item()]}]

    out = StringIO()
    call_command("import_harvest_tables", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id ch.bafu : ch.bafu1" in out
    assert "Obsolete organizations found: ch.bafu2" in out

    org_1.refresh_from_db()
    assert org_1.organization_id == "ch.bafu1"
    assert org_1.name_de == "Bundesamt für Umwelt"
    assert org_1.name_fr == "Office fédéral de l'environnement"
    assert org_1.name_en == "Federal Office for the Environment"
    assert org_1.name_it == "Ufficio federale dell'ambiente"
    assert org_1.name_rm == "Uffizi federal per l'ambient"
    assert org_1.acronym_de == "BAFU"
    assert org_1.acronym_fr == "OFEV"
    assert org_1.acronym_en == "FOEN"
    assert org_1.acronym_it == "UFAM"
    assert org_1.acronym_rm == "UFAM"
    assert org_1.data_source == Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION
    assert org_1.data_source_ids == ["ch.bafu"]

    org_2.refresh_from_db()
    assert org_2.data_source_ids == []


@patch("organization.models.Client")
def test_command_uses_one_to_many_organization_mapping(client, dynamodb, db):
    org = Organization(
        organization_id="ch.bafu",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION,
        data_source_ids=[],
    )
    org.save()

    org_in_1 = OrganizationImport(
        provider_id="ch.bafu1",
        name_de="y",
        name_fr="y",
        name_en="y",
        name_it="y",
        name_rm="y",
        acronym_de="y",
        acronym_fr="y",
        acronym_en="y",
        acronym_it="y",
        acronym_rm="y",
    )
    org_in_2 = OrganizationImport(
        provider_id="ch.bafu2",
        name_de="Bundesamt für Umwelt",
        name_fr="Office fédéral de l'environnement",
        name_en="Federal Office for the Environment",
        name_it="Ufficio federale dell'ambiente",
        name_rm="Uffizi federal per l'ambient",
        acronym_de="BAFU",
        acronym_fr="OFEV",
        acronym_en="FOEN",
        acronym_it="UFAM",
        acronym_rm="UFAM",
    )

    OrganizationMapping(
        provider_id_prefix="ch.bafu1", organization_id="ch.bafu", update_organization=False
    ).save()
    OrganizationMapping(
        provider_id_prefix="ch.bafu2", organization_id="ch.bafu", update_organization=True
    ).save()

    dynamodb.get_paginator().paginate.return_value = [
        {"Items": [org_in_1.as_dynamodb_item(), org_in_2.as_dynamodb_item()]}
    ]

    out = StringIO()
    call_command("import_harvest_tables", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for provider_id ch.bafu1 : ch.bafu" in out
    assert "Mapping found for provider_id ch.bafu2 : ch.bafu" in out

    org.refresh_from_db()
    assert org.organization_id == "ch.bafu"
    assert org.name_de == "Bundesamt für Umwelt"
    assert org.name_fr == "Office fédéral de l'environnement"
    assert org.name_en == "Federal Office for the Environment"
    assert org.name_it == "Ufficio federale dell'ambiente"
    assert org.name_rm == "Uffizi federal per l'ambient"
    assert org.acronym_de == "BAFU"
    assert org.acronym_fr == "OFEV"
    assert org.acronym_en == "FOEN"
    assert org.acronym_it == "UFAM"
    assert org.acronym_rm == "UFAM"
    assert org.data_source == Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION
    assert org.data_source_ids == ["ch.bafu1", "ch.bafu2"]


@patch("organization.models.Client")
def test_command_cleans_organizations(client, dynamodb, db):
    Organization(
        organization_id="ch.unused",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION,
        data_source_ids=["ch.unused"],
    ).save()
    Organization(
        organization_id="ch.bafu",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION,
        data_source_ids=["ch.bafu"],
    ).save()
    Organization(
        organization_id="ch.bafu-copy",
        name_de="x",
        name_fr="x",
        name_en="x",
        name_it="x",
        name_rm="x",
        acronym_de="x",
        acronym_fr="x",
        acronym_en="x",
        acronym_it="x",
        acronym_rm="x",
        data_source=Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION,
        data_source_ids=["ch.bafu"],
    ).save()

    org_in = OrganizationImport(
        provider_id="ch.bafu",
        name_de="Bundesamt für Umwelt",
        name_fr="Office fédéral de l'environnement",
        name_en="Federal Office for the Environment",
        name_it="Ufficio federale dell'ambiente",
        name_rm="Uffizi federal per l'ambient",
        acronym_de="BAFU",
        acronym_fr="OFEV",
        acronym_en="FOEN",
        acronym_it="UFAM",
        acronym_rm="UFAM",
    )

    dynamodb.get_paginator().paginate.return_value = [{"Items": [org_in.as_dynamodb_item()]}]

    # only report
    out = StringIO()
    call_command("import_harvest_tables", organizations=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removed data_source_ids (provider) found: ch.unused" in out
    assert "Obsolete organizations found: ch.bafu-copy" in out

    assert Organization.objects.count() == 3

    # clean
    out = StringIO()
    call_command("import_harvest_tables", organizations=True, clean=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removing obsolete data_source_id (provider) ch.unused" in out
    assert "Removing obsolete organization ch.bafu-copy" in out
    assert "Removing obsolete organization ch.unused" in out

    assert Organization.objects.count() == 1
    assert Organization.objects.filter(organization_id="ch.bafu").first()


# --------------------------------------------------------------------------------------------------
# Datasets
# --------------------------------------------------------------------------------------------------


def test_command_creates_dataset(dynamodb, db):
    ds_in = DatasetImport(
        dataset_id="ch.bafu.moose",
        title_de="Rote Liste Moose",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        title_it="Lista rossa delle biofite minacciate",
        title_rm="Glista cotschna dals mistgels",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        description_it="Description (IT)",
        description_rm="Description (RM)",
        attribution=["ch.bafu"],
        provider=["ch.bafu"],
        geocat_id="abcd",
    )

    dynamodb.get_paginator().paginate.return_value = [{"Items": [ds_in.as_dynamodb_item()]}]

    out = StringIO()
    call_command("import_harvest_tables", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataset with dataset_id ch.bafu.moose does not exist yet, creating a new one." in out

    ds_out = Dataset.objects.first()
    assert ds_out
    assert ds_out.dataset_id == "ch.bafu.moose"
    assert ds_out.title_short_de == "Rote Liste Moose"
    assert ds_out.title_short_fr == "Liste rouge mousses"
    assert ds_out.title_short_en == "Red list bryophytes"
    assert ds_out.title_short_it == "Lista rossa delle biofite minacciate"
    assert ds_out.title_short_rm == "Glista cotschna dals mistgels"
    assert ds_out.description_de == "Description (DE)"
    assert ds_out.description_fr == "Description (FR)"
    assert ds_out.description_en == "Description (EN)"
    assert ds_out.description_it == "Description (IT)"
    assert ds_out.description_rm == "Description (RM)"
    assert ds_out.geocat_id == "abcd"
    assert ds_out.data_source == Dataset.DATA_SOURCE_CHOICE_BOD_DATASET
    assert ds_out.data_source_ids == ["ch.bafu.moose"]


def test_command_updates_dataset(dynamodb, db):
    Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
        geocat_id="x",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
        data_source_ids=[],
    ).save()

    ds_in = DatasetImport(
        dataset_id="ch.bafu.moose",
        title_de="Rote Liste Moose",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        title_it="Lista rossa delle biofite minacciate",
        title_rm="Glista cotschna dals mistgels",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        description_it="Description (IT)",
        description_rm="Description (RM)",
        attribution=["ch.bafu"],
        provider=["ch.bafu"],
        geocat_id="abcd",
    )

    dynamodb.get_paginator().paginate.return_value = [{"Items": [ds_in.as_dynamodb_item()]}]

    out = StringIO()
    call_command("import_harvest_tables", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Dataset with dataset_id ch.bafu.moose already exists" in out

    ds_out = Dataset.objects.first()
    assert ds_out
    assert ds_out.dataset_id == "ch.bafu.moose"
    assert ds_out.title_short_de == "Rote Liste Moose"
    assert ds_out.title_short_fr == "Liste rouge mousses"
    assert ds_out.title_short_en == "Red list bryophytes"
    assert ds_out.title_short_it == "Lista rossa delle biofite minacciate"
    assert ds_out.title_short_rm == "Glista cotschna dals mistgels"
    assert ds_out.description_de == "Description (DE)"
    assert ds_out.description_fr == "Description (FR)"
    assert ds_out.description_en == "Description (EN)"
    assert ds_out.description_it == "Description (IT)"
    assert ds_out.description_rm == "Description (RM)"
    assert ds_out.geocat_id == "abcd"
    assert ds_out.data_source == Dataset.DATA_SOURCE_CHOICE_BOD_DATASET
    assert ds_out.data_source_ids == ["ch.bafu.moose"]


def test_command_uses_one_to_one_dataset_mapping(dynamodb, db):
    ds_1 = Dataset(
        dataset_id="ch.bafu.moose1",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
        geocat_id="x1",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
        data_source_ids=["ch.bafu.moose"],
    )
    ds_1.save()
    ds_2 = Dataset(
        dataset_id="ch.bafu.moose2",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
        geocat_id="x2",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
        data_source_ids=["ch.bafu.moose"],
    )
    ds_2.save()

    ds_in = DatasetImport(
        dataset_id="ch.bafu.moose",
        title_de="Rote Liste Moose",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        title_it="Lista rossa delle biofite minacciate",
        title_rm="Glista cotschna dals mistgels",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        description_it="Description (IT)",
        description_rm="Description (RM)",
        attribution=["ch.bafu"],
        provider=["ch.bafu"],
        geocat_id="abcd",
    )

    DatasetMapping(
        dataset_id_prefix="ch.bafu.moose", dataset_id="ch.bafu.moose1", update_dataset=True
    ).save()

    dynamodb.get_paginator().paginate.return_value = [{"Items": [ds_in.as_dynamodb_item()]}]

    out = StringIO()
    call_command("import_harvest_tables", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for dataset_id ch.bafu.moose : ch.bafu.moose1" in out
    assert "Obsolete datasets found: ch.bafu.moose2" in out

    ds_1.refresh_from_db()
    assert ds_1.dataset_id == "ch.bafu.moose1"
    assert ds_1.title_short_de == "Rote Liste Moose"
    assert ds_1.title_short_fr == "Liste rouge mousses"
    assert ds_1.title_short_en == "Red list bryophytes"
    assert ds_1.title_short_it == "Lista rossa delle biofite minacciate"
    assert ds_1.title_short_rm == "Glista cotschna dals mistgels"
    assert ds_1.description_de == "Description (DE)"
    assert ds_1.description_fr == "Description (FR)"
    assert ds_1.description_en == "Description (EN)"
    assert ds_1.description_it == "Description (IT)"
    assert ds_1.description_rm == "Description (RM)"
    assert ds_1.geocat_id == "abcd"
    assert ds_1.data_source == Dataset.DATA_SOURCE_CHOICE_BOD_DATASET
    assert ds_1.data_source_ids == ["ch.bafu.moose"]

    ds_2.refresh_from_db()
    assert ds_2.data_source_ids == []


def test_command_uses_one_to_many_dataset_mapping(dynamodb, db):
    ds = Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
        geocat_id="x",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
        data_source_ids=[],
    )
    ds.save()

    ds_in_1 = DatasetImport(
        dataset_id="ch.bafu.moose1",
        title_de="y",
        title_fr="y",
        title_en="y",
        title_it="y",
        title_rm="y",
        description_de="y",
        description_fr="y",
        description_en="y",
        description_it="y",
        description_rm="y",
        attribution=["ch.bafu"],
        provider=["ch.bafu"],
        geocat_id="y",
    )
    ds_in_2 = DatasetImport(
        dataset_id="ch.bafu.moose2",
        title_de="Rote Liste Moose",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        title_it="Lista rossa delle biofite minacciate",
        title_rm="Glista cotschna dals mistgels",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        description_it="Description (IT)",
        description_rm="Description (RM)",
        attribution=["ch.bafu"],
        provider=["ch.bafu"],
        geocat_id="abcd",
    )

    DatasetMapping(
        dataset_id_prefix="ch.bafu.moose1", dataset_id="ch.bafu.moose", update_dataset=False
    ).save()
    DatasetMapping(
        dataset_id_prefix="ch.bafu.moose2", dataset_id="ch.bafu.moose", update_dataset=True
    ).save()

    dynamodb.get_paginator().paginate.return_value = [
        {"Items": [ds_in_1.as_dynamodb_item(), ds_in_2.as_dynamodb_item()]}
    ]

    out = StringIO()
    call_command("import_harvest_tables", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Mapping found for dataset_id ch.bafu.moose1 : ch.bafu.moose" in out
    assert "Mapping found for dataset_id ch.bafu.moose2 : ch.bafu.moose" in out

    ds.refresh_from_db()
    assert ds.dataset_id == "ch.bafu.moose"
    assert ds.title_short_de == "Rote Liste Moose"
    assert ds.title_short_fr == "Liste rouge mousses"
    assert ds.title_short_en == "Red list bryophytes"
    assert ds.title_short_it == "Lista rossa delle biofite minacciate"
    assert ds.title_short_rm == "Glista cotschna dals mistgels"
    assert ds.description_de == "Description (DE)"
    assert ds.description_fr == "Description (FR)"
    assert ds.description_en == "Description (EN)"
    assert ds.description_it == "Description (IT)"
    assert ds.description_rm == "Description (RM)"
    assert ds.geocat_id == "abcd"
    assert ds.data_source == Dataset.DATA_SOURCE_CHOICE_BOD_DATASET
    assert ds.data_source_ids == ["ch.bafu.moose1", "ch.bafu.moose2"]


def test_command_cleans_datasets(dynamodb, db):
    Dataset(
        dataset_id="ch.bafu.unused",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
        geocat_id="x",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
        data_source_ids=["ch.bafu.unused"],
    ).save()
    Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
        geocat_id="y",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
        data_source_ids=["ch.bafu.moose"],
    ).save()
    Dataset(
        dataset_id="ch.bafu.moose-copy",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
        geocat_id="z",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
        data_source_ids=["ch.bafu.moose"],
    ).save()

    ds_in = DatasetImport(
        dataset_id="ch.bafu.moose",
        title_de="Rote Liste Moose",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        title_it="Lista rossa delle biofite minacciate",
        title_rm="Glista cotschna dals mistgels",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        description_it="Description (IT)",
        description_rm="Description (RM)",
        attribution=["ch.bafu"],
        provider=["ch.bafu"],
        geocat_id="abcd",
    )

    dynamodb.get_paginator().paginate.return_value = [{"Items": [ds_in.as_dynamodb_item()]}]

    # only report
    out = StringIO()
    call_command("import_harvest_tables", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removed data_source_id (dataset) found: ch.bafu.unused" in out
    assert "Obsolete datasets found: ch.bafu.moose-copy" in out

    assert Dataset.objects.count() == 3

    # clean
    out = StringIO()
    call_command("import_harvest_tables", datasets=True, clean=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Removing obsolete data_source_id (dataset) ch.bafu.unused" in out
    assert "Removing obsolete dataset ch.bafu.moose-copy" in out
    assert "Removing obsolete dataset ch.bafu.unused" in out

    assert Dataset.objects.count() == 1
    assert Dataset.objects.filter(dataset_id="ch.bafu.moose").first()


@patch("organization.models.Client")
def test_command_matches_existing_dataset_provider(client, dynamodb, db):
    org = Organization(
        organization_id="ch.bafu",
        name_de="Bundesamt für Umwelt",
        name_fr="Office fédéral de l'environnement",
        name_en="Federal Office for the Environment",
        name_it="Ufficio federale dell'ambiente",
        name_rm="Uffizi federal per l'ambient",
        acronym_de="BAFU",
        acronym_fr="OFEV",
        acronym_en="FOEN",
        acronym_it="UFAM",
        acronym_rm="UFAM",
    )
    org.save()

    unit = Unit(organization=org, unit_id="ch.bafu.unit", name_de="x", name_fr="x", name_en="x")
    unit.save()

    ds = Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
        geocat_id="y",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
        data_source_ids=["ch.bafu.moose"],
    )
    ds.save()

    DatasetToUnit(dataset=ds, unit=unit, role=DatasetToUnit.ROLE_OWNER).save()
    DatasetToUnit(dataset=ds, unit=unit, role=DatasetToUnit.ROLE_MAINTAINER).save()

    ds_in = DatasetImport(
        dataset_id="ch.bafu.moose",
        title_de="Rote Liste Moose",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        title_it="Lista rossa delle biofite minacciate",
        title_rm="Glista cotschna dals mistgels",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        description_it="Description (IT)",
        description_rm="Description (RM)",
        attribution=["ch.bafu"],
        provider=["ch.bafu"],
        geocat_id="abcd",
    )

    dynamodb.get_paginator().paginate.return_value = [{"Items": [ds_in.as_dynamodb_item()]}]

    out = StringIO()
    call_command("import_harvest_tables", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    ds.refresh_from_db()
    assert ds.dataset_id == "ch.bafu.moose"
    assert ds.data_source == Dataset.DATA_SOURCE_CHOICE_BOD_DATASET
    assert ds.data_source_ids == ["ch.bafu.moose"]
    assert {
        ds_unit.role: (ds_unit.unit.organization.organization_id, ds_unit.unit.unit_id)
        for ds_unit in ds.dataset_units.all()
    } == {
        "maintainer": ("ch.bafu", "ch.bafu.unit"),
        DatasetToUnit.ROLE_OWNER: ("ch.bafu", Unit.DEFAULT_UNIT_ID),
    }


@patch("organization.models.Client")
def test_command_uses_dataset_unit_mapping(client, dynamodb, db):
    org = Organization(
        organization_id="ch.bafu",
        name_de="Bundesamt für Umwelt",
        name_fr="Office fédéral de l'environnement",
        name_en="Federal Office for the Environment",
        name_it="Ufficio federale dell'ambiente",
        name_rm="Uffizi federal per l'ambient",
        acronym_de="BAFU",
        acronym_fr="OFEV",
        acronym_en="FOEN",
        acronym_it="UFAM",
        acronym_rm="UFAM",
    )
    org.save()

    unit = Unit(organization=org, unit_id="ch.bafu.unit", name_de="x", name_fr="x", name_en="x")
    unit.save()

    ds = Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
        geocat_id="y",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
        data_source_ids=["ch.bafu.moose"],
    )
    ds.save()

    DatasetToUnitMapping(
        dataset_id_prefix="ch.bafu", organization_id="ch.bafu", unit_id="ch.bafu.unit"
    ).save()

    ds_in = DatasetImport(
        dataset_id="ch.bafu.moose",
        title_de="Rote Liste Moose",
        title_fr="Liste rouge mousses",
        title_en="Red list bryophytes",
        title_it="Lista rossa delle biofite minacciate",
        title_rm="Glista cotschna dals mistgels",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        description_it="Description (IT)",
        description_rm="Description (RM)",
        attribution=["ch.bafu"],
        provider=["ch.bafu"],
        geocat_id="abcd",
    )

    dynamodb.get_paginator().paginate.return_value = [{"Items": [ds_in.as_dynamodb_item()]}]

    out = StringIO()
    call_command("import_harvest_tables", datasets=True, verbosity=2, stdout=out)
    out = out.getvalue()

    ds.refresh_from_db()
    assert ds.dataset_id == "ch.bafu.moose"
    assert ds.data_source == Dataset.DATA_SOURCE_CHOICE_BOD_DATASET
    assert ds.data_source_ids == ["ch.bafu.moose"]
    assert {
        ds_unit.role: (ds_unit.unit.organization.organization_id, ds_unit.unit.unit_id)
        for ds_unit in ds.dataset_units.all()
    } == {DatasetToUnit.ROLE_OWNER: ("ch.bafu", "ch.bafu.unit")}


# --------------------------------------------------------------------------------------------------
# Distributions
# --------------------------------------------------------------------------------------------------
# FIXME: Add tests


# --------------------------------------------------------------------------------------------------
# Keywords
# --------------------------------------------------------------------------------------------------
def test_command_creates_and_updates_keywords(dynamodb, db):
    ds = Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
        geocat_id="abcd",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
    )
    ds.save()

    kw_1 = Keyword(
        type="theme",
        thesaurus_id="geonetwork.thesaurus.external.theme.gemet",
        thesaurus_url="https://example.com/theme.gemet",
        thesaurus_date=None,
        concept="http://www.eionet.europa.eu/gemet/concept/25",
        translation_de="Unfall",
        translation_fr="accident",
        translation_en="accident",
        translation_it="incidente",
        translation_rm=None,
    )
    kw_2 = Keyword(
        type="theme",
        thesaurus_id="geonetwork.thesaurus.external.theme.gemet",
        thesaurus_url="https://example.com/theme.gemet",
        thesaurus_date=None,
        concept="http://www.eionet.europa.eu/gemet/concept/245",
        translation_de="Luft",
        translation_fr="air",
        translation_en="air",
        translation_it="aria",
        translation_rm=None,
    )
    kw_3 = Keyword(
        type="theme",
        thesaurus_id="geonetwork.thesaurus.external.theme.gemet",
        thesaurus_url="https://example.com/theme.gemet",
        thesaurus_date=None,
        concept="http://www.eionet.europa.eu/gemet/concept/253",
        translation_de="Luftfahrzeug",
        translation_fr="appareil volant",
        translation_en="aircraft",
        translation_it="velivolo",
        translation_rm=None,
    )

    # Create
    keywords = KeywordList(dataset_id="ch.bafu.moose", geocat_id="abcd", keywords=[kw_1, kw_2])
    dynamodb.get_item.return_value = {"Item": keywords.as_dynamodb_item()}

    out = StringIO()
    call_command("import_harvest_tables", keywords=True, verbosity=2, stdout=out)
    out = out.getvalue()

    thesaurus = Thesaurus.objects.first()
    assert thesaurus
    assert thesaurus.thesaurus_id == "geonetwork.thesaurus.external.theme.gemet"
    assert {keyword.keyword_id for keyword in thesaurus.keyword_set.all()} == {
        "http://www.eionet.europa.eu/gemet/concept/25",
        "http://www.eionet.europa.eu/gemet/concept/245",
    }

    keyword = KeywordModel.objects.filter(
        keyword_id="http://www.eionet.europa.eu/gemet/concept/25"
    ).first()
    assert keyword
    assert keyword.label_de == "Unfall"
    assert keyword.label_fr == "accident"
    assert keyword.label_en == "accident"
    assert keyword.label_it == "incidente"
    assert keyword.label_rm is None

    ds.refresh_from_db()
    assert {keyword.keyword_id for keyword in ds.keywords.all()} == {
        "http://www.eionet.europa.eu/gemet/concept/25",
        "http://www.eionet.europa.eu/gemet/concept/245",
    }

    # Update
    keywords = KeywordList(dataset_id="ch.bafu.moose", geocat_id="abcd", keywords=[kw_3, kw_2])
    dynamodb.get_item.return_value = {"Item": keywords.as_dynamodb_item()}

    out = StringIO()
    call_command("import_harvest_tables", keywords=True, verbosity=2, stdout=out)
    out = out.getvalue()

    thesaurus.refresh_from_db()
    assert thesaurus.keyword_set.count() == 3

    ds.refresh_from_db()
    assert {keyword.keyword_id for keyword in ds.keywords.all()} == {
        "http://www.eionet.europa.eu/gemet/concept/245",
        "http://www.eionet.europa.eu/gemet/concept/253",
    }


# --------------------------------------------------------------------------------------------------
# Contacts
# --------------------------------------------------------------------------------------------------
@patch("organization.models.Client")
def test_command_creates_and_updates_contact(client, dynamodb, db):
    ds = Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
        geocat_id="abcd",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
    )
    ds.save()

    org = Organization(
        organization_id="ch.bafu",
        name_de="Bundesamt für Umwelt",
        name_fr="Office fédéral de l'environnement",
        name_en="Federal Office for the Environment",
        name_it="Ufficio federale dell'ambiente",
        name_rm="Uffizi federal per l'ambient",
        acronym_de="BAFU",
        acronym_fr="OFEV",
        acronym_en="FOEN",
        acronym_it="UFAM",
        acronym_rm="UFAM",
    )
    org.save()

    contact = Contact(
        role=DatasetToContact.ROLE_POINT_OF_CONTACT,
        org_name="Bundesamt für Umwelt",
        org_name_de="Bundesamt für Umwelt",
        org_name_fr="Office fédéral de l'environnement",
        org_name_en="Federal Office for the Environment",
        org_name_it="Ufficio federale dell'ambiente",
        org_name_rm="Uffizi federal per l'ambient",
        org_acronym="BAFU",
        org_acronym_de="BAFU",
        org_acronym_fr="OFEV",
        org_acronym_en="FOEN",
        org_acronym_it="UFAM",
        org_acronym_rm="UFAM",
        position_name="Abteilung Luftreinhaltung und Chemikalien",
        position_name_de="Abteilung Luftreinhaltung und Chemikalien",
        position_name_fr="Division Protection de l'air et produits chimiques",
        position_name_en="Air Pollution Control and Chemicals Division",
        position_name_it="Divisione Protezione dell'aria e prodotti chimici",
        position_name_rm="-Missing-",
        contact_voice="123",
        contact_facsimile="456",
        contact_sms="789",
        contact_city="Bern",
        contact_administrative_area="",
        contact_postal_code="3003",
        contact_country="CH",
        contact_electronic_mail_addresses=["chemicals@bafu.admin.ch"],
        contact_delivery_point="",
        online_resources=[
            OnlineResource(
                url="https://www.bafu.admin.ch/",
                url_de="https://www.bafu.admin.ch/de/",
                url_fr="https://www.bafu.admin.ch/fr/",
                url_en="https://www.bafu.admin.ch/en/",
                url_it="https://www.bafu.admin.ch/i/",
                url_rm="https://www.bafu.admin.ch/rm/",
                protocol="WWW:LINK",
                name_de=None,
                name_fr=None,
                name_en=None,
                name_it=None,
                name_rm=None,
                description_de=None,
                description_fr=None,
                description_en=None,
                description_it=None,
                description_rm=None,
                function=None,
            )
        ],
    )

    # Create
    contacts = ContactList(dataset_id="ch.bafu.moose", geocat_id="abcd", contacts=[contact])
    dynamodb.get_item.return_value = {"Item": contacts.as_dynamodb_item()}

    out = StringIO()
    call_command("import_harvest_tables", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    ds.refresh_from_db()
    assert ds.legacy_contacts == [
        {
            "role": DatasetToContact.ROLE_POINT_OF_CONTACT,
            "org_name": "Bundesamt für Umwelt",
            "contact_sms": "789",
            "org_acronym": "BAFU",
            "org_name_de": "Bundesamt für Umwelt",
            "org_name_en": "Federal Office for the Environment",
            "org_name_fr": "Office fédéral de l'environnement",
            "org_name_it": "Ufficio federale dell'ambiente",
            "org_name_rm": "Uffizi federal per l'ambient",
            "contact_city": "Bern",
            "contact_voice": "123",
            "org_acronym_de": "BAFU",
            "org_acronym_en": "FOEN",
            "org_acronym_fr": "OFEV",
            "org_acronym_it": "UFAM",
            "org_acronym_rm": "UFAM",
            "contact_country": "CH",
            "online_resources": [
                {
                    "url": "https://www.bafu.admin.ch/",
                    "url_de": "https://www.bafu.admin.ch/de/",
                    "url_en": "https://www.bafu.admin.ch/en/",
                    "url_fr": "https://www.bafu.admin.ch/fr/",
                    "url_it": "https://www.bafu.admin.ch/i/",
                    "url_rm": "https://www.bafu.admin.ch/rm/",
                    "name_de": None,
                    "name_en": None,
                    "name_fr": None,
                    "name_it": None,
                    "name_rm": None,
                    "function": None,
                    "protocol": "WWW:LINK",
                    "description_de": None,
                    "description_en": None,
                    "description_fr": None,
                    "description_it": None,
                    "description_rm": None,
                }
            ],
            "position_name_de": "Abteilung Luftreinhaltung und Chemikalien",
            "position_name_en": "Air Pollution Control and Chemicals Division",
            "position_name_fr": "Division Protection de l'air et produits chimiques",
            "position_name_it": "Divisione Protezione dell'aria e prodotti chimici",
            "position_name_rm": "-Missing-",
            "contact_facsimile": "456",
            "contact_postal_code": "3003",
            "contact_delivery_point": "",
            "contact_administrative_area": "",
            "contact_electronic_mail_addresses": ["chemicals@bafu.admin.ch"],
        }
    ]

    ds_contact = ds.dataset_contacts.first()
    assert ds_contact
    assert ds_contact.role == DatasetToContact.ROLE_POINT_OF_CONTACT
    assert ds_contact.contact.organization == org
    assert ds_contact.contact.name_de == "Abteilung Luftreinhaltung und Chemikalien"
    assert ds_contact.contact.name_fr == "Division Protection de l'air et produits chimiques"
    assert ds_contact.contact.name_en == "Air Pollution Control and Chemicals Division"
    assert ds_contact.contact.name_it == "Divisione Protezione dell'aria e prodotti chimici"
    assert ds_contact.contact.name_rm == "-Missing-"
    assert ds_contact.contact.email == "chemicals@bafu.admin.ch"
    assert ds_contact.contact.phone == "123"
    assert ds_contact.contact.address_administrative_area == ""
    assert ds_contact.contact.address_delivery_point == ""
    assert ds_contact.contact.address_postal_code == "3003"
    assert ds_contact.contact.address_city == "Bern"
    assert ds_contact.contact.address_country == "CH"
    assert ds_contact.contact.url_de == "https://www.bafu.admin.ch/de/"
    assert ds_contact.contact.url_fr == "https://www.bafu.admin.ch/fr/"
    assert ds_contact.contact.url_en == "https://www.bafu.admin.ch/en/"
    assert ds_contact.contact.url_it == "https://www.bafu.admin.ch/i/"
    assert ds_contact.contact.url_rm == "https://www.bafu.admin.ch/rm/"

    # Update
    contact.role = DatasetToContact.ROLE_OWNER
    contact.position_name_rm = None
    contacts = ContactList(dataset_id="ch.bafu.moose", geocat_id="abcd", contacts=[contact])
    dynamodb.get_item.return_value = {"Item": contacts.as_dynamodb_item()}

    out = StringIO()
    call_command("import_harvest_tables", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert (
        "Existing contact ch.bafu (Air Pollution Control and Chemicals Division) for owner differs"
        in out
    )

    ds.refresh_from_db()
    assert ds.legacy_contacts[0]["role"] == DatasetToContact.ROLE_OWNER
    assert ds.legacy_contacts[0]["position_name_rm"] is None

    assert DatasetToContact.objects.count() == 1

    ds_contact = ds.dataset_contacts.first()
    assert ds_contact
    assert ds_contact.role == DatasetToContact.ROLE_OWNER
    assert ds_contact.contact.name_rm == "-Missing-"


@patch("organization.models.Client")
def test_command_uses_contact_mapping(client, dynamodb, db):
    ds = Dataset(
        dataset_id="ch.bafu.moose",
        title_short_de="x",
        title_short_fr="x",
        title_short_en="x",
        title_short_it="x",
        title_short_rm="x",
        description_de="x",
        description_fr="x",
        description_en="x",
        description_it="x",
        description_rm="x",
        geocat_id="abcd",
        data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
    )
    ds.save()

    org = Organization(
        organization_id="ch.bafu",
        name_de="Bundesamt für Umwelt",
        name_fr="Office fédéral de l'environnement",
        name_en="Federal Office for the Environment",
        name_it="Ufficio federale dell'ambiente",
        name_rm="Uffizi federal per l'ambient",
        acronym_de="BAFU",
        acronym_fr="OFEV",
        acronym_en="FOEN",
        acronym_it="UFAM",
        acronym_rm="UFAM",
    )
    org.save()

    ContactModel(organization=org, name_en="contact").save()

    DatasetToContactMapping(
        dataset_id_prefix="ch.bafu.moo",
        role=DatasetToContact.ROLE_POINT_OF_CONTACT,
        organization_id="ch.bafu",
        contact_name_en="contact",
    ).save()

    contact = Contact(
        role=DatasetToContact.ROLE_POINT_OF_CONTACT,
        org_name="Bundesamt für Umwelt",
        org_name_de="Bundesamt für Umwelt",
        org_name_fr="Office fédéral de l'environnement",
        org_name_en="Federal Office for the Environment",
        org_name_it="Ufficio federale dell'ambiente",
        org_name_rm="Uffizi federal per l'ambient",
        org_acronym="BAFU",
        org_acronym_de="BAFU",
        org_acronym_fr="OFEV",
        org_acronym_en="FOEN",
        org_acronym_it="UFAM",
        org_acronym_rm="UFAM",
        position_name="Abteilung Luftreinhaltung und Chemikalien",
        position_name_de="Abteilung Luftreinhaltung und Chemikalien",
        position_name_fr="Division Protection de l'air et produits chimiques",
        position_name_en="Air Pollution Control and Chemicals Division",
        position_name_it="Divisione Protezione dell'aria e prodotti chimici",
        position_name_rm="-Missing-",
        contact_voice="123",
        contact_facsimile="456",
        contact_sms="789",
        contact_city="Bern",
        contact_administrative_area="",
        contact_postal_code="3003",
        contact_country="CH",
        contact_electronic_mail_addresses=["chemicals@bafu.admin.ch"],
        contact_delivery_point="",
        online_resources=[
            OnlineResource(
                url="https://www.bafu.admin.ch/",
                url_de="https://www.bafu.admin.ch/de/",
                url_fr="https://www.bafu.admin.ch/fr/",
                url_en="https://www.bafu.admin.ch/en/",
                url_it="https://www.bafu.admin.ch/i/",
                url_rm="https://www.bafu.admin.ch/rm/",
                protocol="WWW:LINK",
                name_de=None,
                name_fr=None,
                name_en=None,
                name_it=None,
                name_rm=None,
                description_de=None,
                description_fr=None,
                description_en=None,
                description_it=None,
                description_rm=None,
                function=None,
            )
        ],
    )

    contacts = ContactList(dataset_id="ch.bafu.moose", geocat_id="abcd", contacts=[contact])
    dynamodb.get_item.return_value = {"Item": contacts.as_dynamodb_item()}

    out = StringIO()
    call_command("import_harvest_tables", contacts=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Existing contact ch.bafu (contact) for pointOfContact differs" in out

    ds.refresh_from_db()
    assert ds.legacy_contacts == [
        {
            "role": DatasetToContact.ROLE_POINT_OF_CONTACT,
            "org_name": "Bundesamt für Umwelt",
            "contact_sms": "789",
            "org_acronym": "BAFU",
            "org_name_de": "Bundesamt für Umwelt",
            "org_name_en": "Federal Office for the Environment",
            "org_name_fr": "Office fédéral de l'environnement",
            "org_name_it": "Ufficio federale dell'ambiente",
            "org_name_rm": "Uffizi federal per l'ambient",
            "contact_city": "Bern",
            "contact_voice": "123",
            "org_acronym_de": "BAFU",
            "org_acronym_en": "FOEN",
            "org_acronym_fr": "OFEV",
            "org_acronym_it": "UFAM",
            "org_acronym_rm": "UFAM",
            "contact_country": "CH",
            "online_resources": [
                {
                    "url": "https://www.bafu.admin.ch/",
                    "url_de": "https://www.bafu.admin.ch/de/",
                    "url_en": "https://www.bafu.admin.ch/en/",
                    "url_fr": "https://www.bafu.admin.ch/fr/",
                    "url_it": "https://www.bafu.admin.ch/i/",
                    "url_rm": "https://www.bafu.admin.ch/rm/",
                    "name_de": None,
                    "name_en": None,
                    "name_fr": None,
                    "name_it": None,
                    "name_rm": None,
                    "function": None,
                    "protocol": "WWW:LINK",
                    "description_de": None,
                    "description_en": None,
                    "description_fr": None,
                    "description_it": None,
                    "description_rm": None,
                }
            ],
            "position_name_de": "Abteilung Luftreinhaltung und Chemikalien",
            "position_name_en": "Air Pollution Control and Chemicals Division",
            "position_name_fr": "Division Protection de l'air et produits chimiques",
            "position_name_it": "Divisione Protezione dell'aria e prodotti chimici",
            "position_name_rm": "-Missing-",
            "contact_facsimile": "456",
            "contact_postal_code": "3003",
            "contact_delivery_point": "",
            "contact_administrative_area": "",
            "contact_electronic_mail_addresses": ["chemicals@bafu.admin.ch"],
        }
    ]

    ds_contact = ds.dataset_contacts.first()
    assert ds_contact
    assert ds_contact.role == DatasetToContact.ROLE_POINT_OF_CONTACT
    assert ds_contact.contact.organization == org
    assert ds_contact.contact.name_de is None
    assert ds_contact.contact.name_fr is None
    assert ds_contact.contact.name_en == "contact"
    assert ds_contact.contact.name_it is None
    assert ds_contact.contact.name_rm is None
    assert ds_contact.contact.email is None
    assert ds_contact.contact.phone is None
    assert ds_contact.contact.address_administrative_area is None
    assert ds_contact.contact.address_delivery_point is None
    assert ds_contact.contact.address_postal_code is None
    assert ds_contact.contact.address_city is None
    assert ds_contact.contact.address_country is None
    assert ds_contact.contact.url_de is None
    assert ds_contact.contact.url_fr is None
    assert ds_contact.contact.url_en is None
    assert ds_contact.contact.url_it is None
    assert ds_contact.contact.url_rm is None
