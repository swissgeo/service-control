from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.forms import ModelForm

import pytest

from organization.models import Unit


@patch("organization.models.Client")
def test_object_stored_as_expected_for_valid_input(client, organization):
    unit_in = {
        "organization": organization,
        "unit_id": "ch.bafu.fauna",
        "name_de": "Fauna",
        "name_fr": "Faune",
        "name_en": "Fauna",
        "name_it": "Fauna",
        "name_rm": "Fauna",
    }
    Unit.objects.create(**unit_in)

    units = Unit.objects.all()

    assert len(units) == 1

    actual = Unit.objects.last()
    assert unit_in["name_de"] == actual.name_de
    assert unit_in["name_fr"] == actual.name_fr
    assert unit_in["name_en"] == actual.name_en
    assert unit_in["name_it"] == actual.name_it
    assert unit_in["name_rm"] == actual.name_rm

    assert client.return_value.create_group.called


@patch("organization.models.Client")
def test_object_created_in_db_with_optional_fields_null(client, organization):
    organization_in = {
        "organization": organization,
        "unit_id": "ch.bafu.fauna",
        "name_de": "Fauna",
        "name_fr": "Faune",
        "name_en": "Fauna",
        "name_it": None,
        "name_rm": None,
    }
    Unit.objects.create(**organization_in)

    units = Unit.objects.all()

    assert len(units) == 1

    actual = Unit.objects.last()
    assert actual.unit_id == organization_in["unit_id"]

    assert actual.name_de == organization_in["name_de"]
    assert actual.name_fr == organization_in["name_fr"]
    assert actual.name_en == organization_in["name_en"]
    assert actual.name_it == organization_in["name_it"]
    assert actual.name_rm == organization_in["name_rm"]

    assert client.return_value.create_group.called


def test_raises_exception_when_creating_db_object_with_mandatory_field_null(organization):
    with pytest.raises(ValidationError):
        Unit.objects.create(
            organization=organization,
            name_de=None,
        )


def test_form_valid_for_blank_optional_field(organization):
    class OrganizationUnitForm(ModelForm):
        class Meta:
            model = Unit
            fields = "__all__"  # noqa: DJ007

    data = {
        "organization": organization,
        "unit_id": "ch.bafu.fauna",
        "name_de": "Fauna",
        "name_fr": "Faune",
        "name_en": "Fauna",
    }
    form = OrganizationUnitForm(data)

    assert form.is_valid() is True


def test_form_invalid_for_blank_mandatory_field(organization):
    class OrganizationUnitForm(ModelForm):
        class Meta:
            model = Unit
            fields = "__all__"  # noqa: DJ007

    data = {
        "organization": organization,
        "unit_id": "ch.bafu.fauna",
        "name_de": "Fauna",
        "name_fr": "Faune",
        "name_en": "",  # empty but mandatory field
    }
    form = OrganizationUnitForm(data)

    assert form.is_valid() is False


@patch("organization.models.Client")
def test_raises_exception_for_existing_slug(client, organization):
    Unit.objects.create(
        organization=organization,
        unit_id="ch.bafu.fauna",
        name_de="Fauna",
        name_fr="Faune",
        name_en="Faune",
    )
    with pytest.raises(ValidationError):
        Unit.objects.create(
            organization=organization,
            unit_id="ch.bafu.fauna",
            name_de="Bundesamt für Umwelt",
            name_fr="Office fédéral de l'environnement",
            name_en="Federal Office for the Environment",
        )

    assert Unit.objects.count() == 1
    assert client.return_value.create_group.call_count == 1


@patch("organization.models.Client")
def test_save_updates_records(client, organization):
    model_fields = {
        "organization": organization,
        "unit_id": "ch.bafu.fauna",
        "name_de": "Fau",
        "name_fr": "Faune",
        "name_en": "Fauna",
    }
    Unit.objects.create(**model_fields)
    actual = Unit.objects.first()
    assert actual.name_de == "Fau"
    assert client.return_value.create_group.called

    client.return_value.reset_mock()
    actual.name_de = "Fauna"
    actual.save()
    updated = Unit.objects.first()
    assert updated.name_de == "Fauna"
    assert client.return_value.mock_calls == []

    with pytest.raises(ValidationError):
        Unit.objects.create(
            organization=organization,
            unit_id="ch.bafu.fauna",
            name_de="XXX",
            name_fr="YYY",
            name_en="ZZZ",
        )

    assert Unit.objects.count() == 1
    assert client.return_value.mock_calls == []


@patch("organization.models.Client")
def test_delete_deletes_records(client, organization):
    model_fields = {
        "organization": organization,
        "unit_id": "ch.bafu.fauna",
        "name_de": "Fauna",
        "name_fr": "Faune",
        "name_en": "Fauna",
    }

    Unit.objects.create(**model_fields)
    actual = Unit.objects.first()

    assert client.return_value.create_group.called

    actual.delete()

    assert not Unit.objects.first()
    assert client.return_value.delete_group.called
