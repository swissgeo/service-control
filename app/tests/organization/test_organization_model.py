from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.forms import ModelForm

import pytest

from cognito.utils.client import OrganizationGroup
from organization.models import Organization, Unit
from user.models import CustomUser


@patch("organization.models.Client")
@patch("organization.models.VPClient")
def test_object_stored_as_expected_for_valid_input(vp_client, client, db):
    vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id"
    vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
    vp_client.return_value.create_dataset_contributor_policy.return_value = (
        "mock-contributor-policy-id"
    )
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
    Organization.objects.create(**organization_in)

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

    assert actual.vp_org_admin_policy_id == "mock-policy-id"

    assert client.return_value.create_group.called
    assert vp_client.return_value.create_org_admin_policy.called
    group_arg = vp_client.return_value.create_org_admin_policy.call_args.args[0]
    assert isinstance(group_arg, OrganizationGroup)
    assert group_arg.resource_id == "ch.bafu"
    assert group_arg.name == "O_ch.bafu"

    default_unit = Unit.objects.first()
    assert default_unit is not None
    assert default_unit.unit_id == "default"
    assert default_unit.organization == actual


@patch("organization.models.Client")
@patch("organization.models.VPClient")
def test_object_created_in_db_with_optional_fields_null(vp_client, client, db):
    vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id"
    vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
    vp_client.return_value.create_dataset_contributor_policy.return_value = (
        "mock-contributor-policy-id"
    )
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
    Organization.objects.create(**organization_in)

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
    assert actual.vp_org_admin_policy_id == "mock-policy-id"

    assert client.return_value.create_group.called
    assert vp_client.return_value.create_org_admin_policy.called
    group_arg = vp_client.return_value.create_org_admin_policy.call_args.args[0]
    assert isinstance(group_arg, OrganizationGroup)
    assert group_arg.resource_id == "ch.bafu"
    assert group_arg.name == "O_ch.bafu"

    default_unit = Unit.objects.first()
    assert default_unit is not None
    assert default_unit.unit_id == "default"
    assert default_unit.organization == actual


def test_raises_exception_when_creating_db_object_with_mandatory_field_null(db):
    with pytest.raises(ValidationError):
        Organization.objects.create(name_de=None)


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


@patch("organization.models.Client")
@patch("organization.models.VPClient")
def test_raises_exception_for_existing_slug(vp_client, client, db):
    vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id"
    vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
    vp_client.return_value.create_dataset_contributor_policy.return_value = (
        "mock-contributor-policy-id"
    )
    Organization.objects.create(
        organization_id="ch.bafu",
        name_de="Bundesamt für Umwelt",
        name_fr="Office fédéral de l'environnement",
        name_en="Federal Office for the Environment",
        acronym_de="BAFU",
        acronym_fr="OFEV",
        acronym_en="FOEN",
    )
    with pytest.raises(ValidationError):
        Organization.objects.create(
            organization_id="ch.bafu",
            name_de="XXX",
            name_fr="YYY",
            name_en="ZZZ",
            acronym_de="xxx",
            acronym_fr="yyy",
            acronym_en="zzz",
        )

    assert Organization.objects.count() == 1
    assert client.return_value.create_group.call_count == 2  # for org and default unit
    assert vp_client.return_value.create_org_admin_policy.call_count == 1


@patch("organization.models.Client")
@patch("organization.models.VPClient")
def test_save_updates_records(vp_client, client, db):
    vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id"
    vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
    vp_client.return_value.create_dataset_contributor_policy.return_value = (
        "mock-contributor-policy-id"
    )
    model_fields = {
        "organization_id": "ch.bafu",
        "name_de": "Bundesamt für",
        "name_fr": "Office fédéral de l'environnement",
        "name_en": "Federal Office for the Environment",
        "acronym_de": "BAFU",
        "acronym_fr": "OFEV",
        "acronym_en": "FOEN",
    }
    Organization.objects.create(**model_fields)
    actual = Organization.objects.first()
    assert actual.name_de == "Bundesamt für"

    client.return_value.reset_mock()
    vp_client.return_value.reset_mock()
    vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id-2"
    actual.name_de = "Bundesamt für Umwelt"
    actual.save()
    updated = Organization.objects.first()
    assert updated.name_de == "Bundesamt für Umwelt"
    assert client.return_value.mock_calls == []
    assert vp_client.return_value.mock_calls == []

    with pytest.raises(ValidationError):
        Organization.objects.create(
            organization_id="ch.bafu",
            name_de="XXX",
            name_fr="YYY",
            name_en="ZZZ",
            acronym_de="xxx",
            acronym_fr="yyy",
            acronym_en="zzz",
        )

    assert Organization.objects.count() == 1
    assert client.return_value.mock_calls == []
    assert vp_client.return_value.mock_calls == []


@patch("organization.models.Client")
@patch("organization.models.VPClient")
def test_delete_deletes_records(vp_client, client, db):
    vp_client.return_value.create_org_admin_policy.return_value = "mock-policy-id"
    vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
    vp_client.return_value.create_dataset_contributor_policy.return_value = (
        "mock-contributor-policy-id"
    )
    model_fields = {
        "organization_id": "ch.bafu",
        "name_de": "Bundesamt für",
        "name_fr": "Office fédéral de l'environnement",
        "name_en": "Federal Office for the Environment",
        "acronym_de": "BAFU",
        "acronym_fr": "OFEV",
        "acronym_en": "FOEN",
    }

    Organization.objects.create(**model_fields)
    actual = Organization.objects.first()

    assert client.return_value.create_group.called
    assert vp_client.return_value.create_org_admin_policy.called

    actual.delete()

    assert not Organization.objects.first()
    assert client.return_value.delete_group.called
    assert vp_client.return_value.delete_policy.called
    assert vp_client.return_value.delete_policy.call_args.args[0] == "mock-policy-id"


@patch("organization.models.Client")
@patch("user.models.Client")
@patch("user.extra_audience.Client")
@patch("organization.models.VPClient")
def test_delete_deletes_related_records(
    vp_client, ssm_client, user_client, org_client, organization, django_machine_user_factory
):
    vp_client.return_value.create_dataset_admin_policy.return_value = "mock-admin-policy-id"
    vp_client.return_value.create_dataset_contributor_policy.return_value = (
        "mock-contributor-policy-id"
    )
    unit_in = {
        "organization": organization,
        "unit_id": "ch.bafu.fauna",
        "name_de": "Fauna",
        "name_fr": "Faune",
        "name_en": "Fauna",
        "name_it": None,
        "name_rm": None,
    }
    Unit.objects.create(**unit_in)

    django_machine_user_factory(
        app_id="abc", name="", organization=organization, created_by_user=None
    )

    organization.delete()

    assert not Organization.objects.first()
    assert not Unit.objects.first()
    assert not CustomUser.objects.first()

    assert org_client.return_value.delete_group.call_count == 3
    assert user_client.return_value.delete_app_client.called
    assert ssm_client.return_value.get_parameter.called
    assert ssm_client.return_value.put_parameter.called
    assert user_client.return_value.delete_app_client.called
    assert ssm_client.return_value.get_parameter.called
    assert ssm_client.return_value.put_parameter.called
    assert user_client.return_value.delete_app_client.called
    assert ssm_client.return_value.get_parameter.called
    assert ssm_client.return_value.put_parameter.called
