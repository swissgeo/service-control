from unittest.mock import patch

from asgiref.sync import async_to_sync

from django.core.exceptions import ValidationError
from django.forms import ModelForm

import pytest

from organization.models import Organization, Unit
from utils.testing import AsyncMagicMock


@patch("organization.models.Client", new_callable=AsyncMagicMock)
def test_object_stored_as_expected_for_valid_input(client, db):
    organization_in = {
        "organization_id": "ch.bafu",
        "name_de": "Bundesamt für Umwelt",
        "name_fr": "Office fédéral de l'environnement",
        "name_en": "Federal Office for the Environment",
        "name_it": "Ufficio federale dell'ambiente",
        "name_rm": "Uffizi federal per l'ambient",
        "acronym_de": "BAFU",
        "acronym_fr": "OFEV",
        "acronym_en": "FOEN",
        "acronym_it": "UFAM",
        "acronym_rm": "UFAM",
    }
    async_to_sync(Organization(**organization_in).save_and_sync)()

    organizations = Organization.objects.all()

    assert len(organizations) == 1

    actual = Organization.objects.last()
    assert organization_in["name_de"] == actual.name_de
    assert organization_in["name_fr"] == actual.name_fr
    assert organization_in["name_en"] == actual.name_en
    assert organization_in["name_it"] == actual.name_it
    assert organization_in["name_rm"] == actual.name_rm

    assert organization_in["acronym_de"] == actual.acronym_de
    assert organization_in["acronym_fr"] == actual.acronym_fr
    assert organization_in["acronym_en"] == actual.acronym_en
    assert organization_in["acronym_it"] == actual.acronym_it
    assert organization_in["acronym_rm"] == actual.acronym_rm

    assert client.return_value.create_group.called


@patch("organization.models.Client", new_callable=AsyncMagicMock)
def test_object_created_in_db_with_optional_fields_null(client, db):
    organization_in = {
        "organization_id": "ch.bafu",
        "name_de": "Bundesamt für Umwelt",
        "name_fr": "Office fédéral de l'environnement",
        "name_en": "Federal Office for the Environment",
        "name_it": None,
        "name_rm": None,
        "acronym_de": "BAFU",
        "acronym_fr": "OFEV",
        "acronym_en": "FOEN",
        "acronym_it": None,
        "acronym_rm": None,
    }
    async_to_sync(Organization(**organization_in).save_and_sync)()

    organizations = Organization.objects.all()

    assert len(organizations) == 1

    actual = Organization.objects.last()
    assert actual.organization_id == organization_in["organization_id"]

    assert actual.name_de == organization_in["name_de"]
    assert actual.name_fr == organization_in["name_fr"]
    assert actual.name_en == organization_in["name_en"]
    assert actual.name_it == organization_in["name_it"]
    assert actual.name_rm == organization_in["name_rm"]

    assert actual.acronym_de == organization_in["acronym_de"]
    assert actual.acronym_fr == organization_in["acronym_fr"]
    assert actual.acronym_en == organization_in["acronym_en"]
    assert actual.acronym_it == organization_in["acronym_it"]
    assert actual.acronym_rm == organization_in["acronym_rm"]

    assert client.return_value.create_group.called


def test_raises_exception_when_creating_db_object_with_mandatory_field_null(db):
    with pytest.raises(ValidationError):
        async_to_sync(Organization(name_de=None).save_and_sync)()


def test_form_valid_for_blank_optional_field(db):
    class OrganizationForm(ModelForm):
        class Meta:
            model = Organization
            fields = "__all__"  # noqa: DJ007

    data = {
        "organization_id": "ch.bafu",
        "name_de": "Bundesamt für Umwelt",
        "name_fr": "Office fédéral de l'environnement",
        "name_en": "Federal Office for the Environment",
        "acronym_de": "BAFU",
        "acronym_fr": "OFEV",
        "acronym_en": "FOEN",
    }
    form = OrganizationForm(data)

    assert form.is_valid() is True


def test_form_invalid_for_blank_mandatory_field(db):
    class OrganizationForm(ModelForm):
        class Meta:
            model = Organization
            fields = "__all__"  # noqa: DJ007

    data = {
        "organization_id": "ch.bafu",
        "name_de": "Bundesamt für Umwelt",
        "name_fr": "Office fédéral de l'environnement",
        "name_en": "Federal Office for the Environment",
        "acronym_de": "BAFU",
        "acronym_fr": "OFEV",
        "acronym_en": "",  # empty but mandatory field
    }
    form = OrganizationForm(data)

    assert form.is_valid() is False


@patch("organization.models.Client", new_callable=AsyncMagicMock)
def test_raises_exception_for_existing_slug(client, db):
    async_to_sync(
        Organization(
            organization_id="ch.bafu",
            name_de="Bundesamt für Umwelt",
            name_fr="Office fédéral de l'environnement",
            name_en="Federal Office for the Environment",
            acronym_de="BAFU",
            acronym_fr="OFEV",
            acronym_en="FOEN",
        ).save_and_sync
    )()
    with pytest.raises(ValidationError):
        async_to_sync(
            Organization(
                organization_id="ch.bafu",
                name_de="XXX",
                name_fr="YYY",
                name_en="ZZZ",
                acronym_de="xxx",
                acronym_fr="yyy",
                acronym_en="zzz",
            ).save_and_sync
        )()

    assert Organization.objects.count() == 1
    assert client.return_value.create_group.call_count == 1


@patch("organization.models.Client", new_callable=AsyncMagicMock)
def test_save_updates_records(client, db):
    model_fields = {
        "organization_id": "ch.bafu",
        "name_de": "Bundesamt für",
        "name_fr": "Office fédéral de l'environnement",
        "name_en": "Federal Office for the Environment",
        "acronym_de": "BAFU",
        "acronym_fr": "OFEV",
        "acronym_en": "FOEN",
    }
    async_to_sync(Organization(**model_fields).save_and_sync)()
    actual = Organization.objects.first()
    assert actual.name_de == "Bundesamt für"
    assert client.return_value.create_group.called

    client.return_value.reset_mock()
    actual.name_de = "Bundesamt für Umwelt"
    async_to_sync(actual.save_and_sync)()
    updated = Organization.objects.first()
    assert updated.name_de == "Bundesamt für Umwelt"
    assert client.return_value.mock_calls == []

    with pytest.raises(ValidationError):
        async_to_sync(
            Organization(
                organization_id="ch.bafu",
                name_de="XXX",
                name_fr="YYY",
                name_en="ZZZ",
                acronym_de="xxx",
                acronym_fr="yyy",
                acronym_en="zzz",
            ).save_and_sync
        )()

    assert Organization.objects.count() == 1
    assert client.return_value.mock_calls == []


@patch("organization.models.Client", new_callable=AsyncMagicMock)
def test_delete_deletes_records(client, db):
    model_fields = {
        "organization_id": "ch.bafu",
        "name_de": "Bundesamt für",
        "name_fr": "Office fédéral de l'environnement",
        "name_en": "Federal Office for the Environment",
        "acronym_de": "BAFU",
        "acronym_fr": "OFEV",
        "acronym_en": "FOEN",
    }

    async_to_sync(Organization(**model_fields).save_and_sync)()
    actual = Organization.objects.first()

    assert client.return_value.create_group.called

    async_to_sync(actual.delete_and_sync)()

    assert not Organization.objects.first()
    assert client.return_value.delete_group.called


@patch("organization.models.Client", new_callable=AsyncMagicMock)
def test_delete_deletes_related_records(client, db):
    organization = Organization(
        organization_id="ch.bafu",
        name_de="Bundesamt für",
        name_fr="Office fédéral de l'environnement",
        name_en="Federal Office for the Environment",
        acronym_de="BAFU",
        acronym_fr="OFEV",
        acronym_en="FOEN",
    )
    async_to_sync(organization.save_and_sync)()

    unit = Unit(
        organization=organization,
        unit_id="ch.bafu.fauna",
        name_de="Fauna",
        name_fr="Faune",
        name_en="Fauna",
    )
    async_to_sync(unit.save_and_sync)()

    assert client.return_value.create_group.call_count == 2

    async_to_sync(organization.delete_and_sync)()
    assert not Organization.objects.first()
    assert not Unit.objects.first()
    assert client.return_value.delete_group.call_count == 2
