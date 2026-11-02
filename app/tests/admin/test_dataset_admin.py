from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.urls import reverse

import pytest

from dataset.admin import DatasetAdmin
from dataset.models import Dataset

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


# Read-only fields tests


@pytest.fixture(name="dataset_admin")
def fixture_dataset_admin():
    return DatasetAdmin(Dataset, AdminSite())


@pytest.fixture(name="admin_request")
def fixture_admin_request():
    return RequestFactory().get("/admin/")


def make_dataset(data_source: Dataset.DataSource) -> Dataset:
    return Dataset(
        dataset_id="dataset.id",
        data_source=data_source,
        title_de="Title (DE)",
        title_fr="Title (FR)",
        title_en="Title (EN)",
        description_de="Description (DE)",
        description_fr="Description (FR)",
        description_en="Description (EN)",
    )


def test_get_readonly_fields_add_view(dataset_admin, admin_request):
    """Without an existing object (add view) only the static readonly fields apply."""
    assert dataset_admin.get_readonly_fields(admin_request, None) == dataset_admin.readonly_fields


def test_get_readonly_fields_user_input(dataset_admin, admin_request):
    """User-input datasets only have the static readonly fields plus the dataset_id."""
    obj = make_dataset(Dataset.DataSource.USER_INPUT)
    readonly = dataset_admin.get_readonly_fields(admin_request, obj)
    assert readonly == ("dataset_id", *dataset_admin.readonly_fields)
    # Manually editable fields must stay editable
    assert "status" not in readonly
    assert "title_de" not in readonly
    assert "concepts" not in readonly


@pytest.mark.parametrize(
    ("data_source", "expected_fields"),
    [
        (
            Dataset.DataSource.BOD_DATASET,
            [
                "data_source",
                "data_source_ids",
                "geocat_id",
                "attribution",
                "concepts",
                "title_de",
                "title_fr",
                "title_short_de",
                "title_short_fr",
                "description_de",
                "description_fr",
            ],
        ),
        (
            Dataset.DataSource.GEODIENSTE,
            [
                "data_source",
                "data_source_ids",
                "geocat_id",
                "attribution",
                "concepts",
                "title_de",
                "title_fr",
                "description_de",
                "description_fr",
                "additional_search_text_de",
                "additional_search_text_fr",
                "legacy_contacts",
                "legacy_part_info_url_de",
                "legacy_part_info_url_fr",
            ],
        ),
    ],
)
def test_get_readonly_fields_harvested(dataset_admin, admin_request, data_source, expected_fields):
    """Harvested datasets have all fields written by the importers read-only."""
    obj = make_dataset(data_source)
    readonly = dataset_admin.get_readonly_fields(admin_request, obj)
    assert "dataset_id" in readonly
    for field in expected_fields:
        assert field in readonly
    # Not imported by the harvesters, must stay editable
    assert "status" not in readonly


def test_get_readonly_fields_harvested_excludes_non_imported(dataset_admin, admin_request):
    """Fields that are not written by the importers must not become read-only."""
    bod = make_dataset(Dataset.DataSource.BOD_DATASET)
    geodienste = make_dataset(Dataset.DataSource.GEODIENSTE)
    readonly_bod = dataset_admin.get_readonly_fields(admin_request, bod)
    readonly_geodienste = dataset_admin.get_readonly_fields(admin_request, geodienste)
    # geodienste.ch-only fields are not read-only for BOD datasets
    for field in (
        "additional_search_text_de",
        "legacy_contacts",
        "legacy_part_info_url_de",
    ):
        assert field not in readonly_bod
    # BOD-only fields are not read-only for geodienste.ch datasets
    for field in (
        "title_short_de",
        "title_short_fr",
        "title_rm",
        "description_rm",
        "additional_search_text_en",
        "additional_search_text_rm",
        "legacy_part_info_url_rm",
    ):
        assert field not in readonly_geodienste
