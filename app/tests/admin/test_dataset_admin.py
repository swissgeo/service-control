from django.conf import settings
from django.urls import reverse

import pytest

from dataset.models import Dataset, DatasetToUnit
from utils.admin import HARVEST_WARNING

ADMIN_HEADERS = {
    "HTTP_X_AUTH_REQUEST_USER": "test",
    "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME": "test",
    "HTTP_X_AUTH_REQUEST_EMAIL": "test@example.com",
    "HTTP_X_AUTH_REQUEST_GROUPS": settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS[0],
}


def create_dataset(sgid: str, dataset_id: str, status: Dataset.Status) -> Dataset:
    return Dataset.objects.create(
        sgid=sgid,
        dataset_id=dataset_id,
        title_de="Title (DE)",
        title_fr="Title (FR)",
        title_en="Title (EN)",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
        status=status,
    )


@pytest.mark.parametrize(
    ("action", "initial_status", "expected_status"),
    [
        ("set_status_draft", Dataset.Status.PUBLISHED, Dataset.Status.DRAFT),
        ("set_status_draft", Dataset.Status.READY, Dataset.Status.DRAFT),
        ("set_status_published", Dataset.Status.DRAFT, Dataset.Status.PUBLISHED),
        ("set_status_published", Dataset.Status.DEPUBLISHED, Dataset.Status.PUBLISHED),
    ],
)
def test_dataset_admin_status_actions(client, db, action, initial_status, expected_status):
    selected = create_dataset("dat_selected", "dataset.selected", initial_status)
    not_selected = create_dataset("dat_not-selected", "dataset.not_selected", initial_status)
    updated_at = selected.updated_at

    response = client.post(
        reverse("admin:dataset_dataset_changelist"),
        {"action": action, "_selected_action": [selected.pk]},
        follow=True,
        **ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert f"1 dataset(s) set to status &#x27;{expected_status.label}&#x27;." in response.text

    selected.refresh_from_db()
    not_selected.refresh_from_db()
    assert selected.status == expected_status
    assert selected.updated_at > updated_at
    assert not_selected.status == initial_status


def test_dataset_admin_status_action_skips_datasets_already_in_status(client, db):
    draft = create_dataset("dat_draft", "dataset.draft", Dataset.Status.DRAFT)
    published = create_dataset("dat_published", "dataset.published", Dataset.Status.PUBLISHED)
    draft_updated_at = draft.updated_at

    response = client.post(
        reverse("admin:dataset_dataset_changelist"),
        {"action": "set_status_draft", "_selected_action": [draft.pk, published.pk]},
        follow=True,
        **ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert "1 dataset(s) set to status &#x27;Draft&#x27;." in response.text

    draft.refresh_from_db()
    published.refresh_from_db()
    assert draft.status == Dataset.Status.DRAFT
    assert draft.updated_at == draft_updated_at
    assert published.status == Dataset.Status.DRAFT


# Harvest warning banner tests
def create_harvested_dataset(
    sgid: str, dataset_id: str, data_source: Dataset.DataSource
) -> Dataset:
    return Dataset.objects.create(
        sgid=sgid,
        dataset_id=dataset_id,
        data_source=data_source,
        title_de="Title (DE)",
        title_fr="Title (FR)",
        title_en="Title (EN)",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
    )


@pytest.mark.parametrize(
    "data_source",
    [Dataset.DataSource.BOD_DATASET, Dataset.DataSource.GEODIENSTE],
)
def test_harvest_warning_shown_for_harvested_dataset(client, db, data_source):
    """A warning banner is shown when editing a harvested dataset."""
    dataset = create_harvested_dataset("dat_harvested", "dataset.harvested", data_source)
    response = client.get(
        reverse("admin:dataset_dataset_change", args=[dataset.pk]),
        follow=True,
        **ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert HARVEST_WARNING in response.text


def test_harvest_warning_not_shown_for_user_input_dataset(client, db):
    """No warning banner is shown when editing a user-input dataset."""
    dataset = create_harvested_dataset("dat_user", "dataset.user", Dataset.DataSource.USER_INPUT)
    response = client.get(
        reverse("admin:dataset_dataset_change", args=[dataset.pk]),
        follow=True,
        **ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert HARVEST_WARNING not in response.text


def test_dataset_admin_owner_organization_filter(client, organization, unit):
    default_unit = organization.unit_set.get(unit_id="default")
    owned = create_dataset("dat_owned", "dataset.owned", Dataset.Status.PUBLISHED)
    owned_twice = create_dataset("dat_owned-twice", "dataset.owned_twice", Dataset.Status.PUBLISHED)
    maintained = create_dataset("dat_maintained", "dataset.maintained", Dataset.Status.PUBLISHED)
    create_dataset("dat_unrelated", "dataset.unrelated", Dataset.Status.PUBLISHED)
    DatasetToUnit.objects.create(dataset=owned, unit=unit, role=DatasetToUnit.Role.OWNER)
    DatasetToUnit.objects.create(dataset=owned_twice, unit=unit, role=DatasetToUnit.Role.OWNER)
    DatasetToUnit.objects.create(
        dataset=owned_twice, unit=default_unit, role=DatasetToUnit.Role.OWNER
    )
    DatasetToUnit.objects.create(dataset=maintained, unit=unit, role=DatasetToUnit.Role.MAINTAINER)

    response = client.get(
        reverse("admin:dataset_dataset_changelist"),
        {"owner_organization": organization.pk},
        **ADMIN_HEADERS,
    )

    assert response.status_code == 200
    result = list(response.context["cl"].queryset.order_by("dataset_id"))
    assert result == [owned, owned_twice]
    assert organization.abbreviation_de in response.text


def test_dataset_admin_shows_owner_organization(client, organization, unit):
    dataset = create_dataset("dat_owned", "dataset.owned", Dataset.Status.PUBLISHED)
    DatasetToUnit.objects.create(dataset=dataset, unit=unit, role=DatasetToUnit.Role.OWNER)
    organization_url = reverse("admin:organization_organization_change", args=[organization.pk])

    response = client.get(
        reverse("admin:dataset_dataset_change", args=[dataset.pk]), **ADMIN_HEADERS
    )

    assert response.status_code == 200
    assert f'<a href="{organization_url}">{organization.name_en}</a>' in response.text


def test_dataset_admin_owner_organization_ignores_other_roles(client, unit):
    dataset = create_dataset("dat_maintained", "dataset.maintained", Dataset.Status.PUBLISHED)
    DatasetToUnit.objects.create(dataset=dataset, unit=unit, role=DatasetToUnit.Role.MAINTAINER)

    response = client.get(
        reverse("admin:dataset_dataset_change", args=[dataset.pk]), **ADMIN_HEADERS
    )

    assert response.status_code == 200
    assert reverse("admin:organization_organization_change", args=[unit.organization.pk]) not in (
        response.text
    )


def test_dataset_admin_list_shows_owner_abbreviation(client, organization, unit):
    default_unit = organization.unit_set.get(unit_id="default")
    owned = create_dataset("dat_owned", "dataset.owned", Dataset.Status.PUBLISHED)
    maintained = create_dataset("dat_maintained", "dataset.maintained", Dataset.Status.PUBLISHED)
    unowned = create_dataset("dat_unowned", "dataset.unowned", Dataset.Status.PUBLISHED)
    DatasetToUnit.objects.create(dataset=owned, unit=unit, role=DatasetToUnit.Role.OWNER)
    DatasetToUnit.objects.create(dataset=owned, unit=default_unit, role=DatasetToUnit.Role.OWNER)
    DatasetToUnit.objects.create(dataset=maintained, unit=unit, role=DatasetToUnit.Role.MAINTAINER)

    # Sort by the owner column to make sure ordering on the annotation works
    response = client.get(reverse("admin:dataset_dataset_changelist"), {"o": "4"}, **ADMIN_HEADERS)

    assert response.status_code == 200
    owners = {ds.pk: ds.owner_abbreviations for ds in response.context["cl"].result_list}
    assert owners == {owned.pk: organization.abbreviation_de, maintained.pk: None, unowned.pk: None}
