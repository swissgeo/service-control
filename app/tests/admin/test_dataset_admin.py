from django.conf import settings
from django.urls import reverse

import pytest

from dataset.models import Dataset

ADMIN_HEADERS = {
    "HTTP_X_AUTH_REQUEST_USER": "test",
    "HTTP_X_AUTH_REQUEST_PREFERRED_USERNAME": "test",
    "HTTP_X_AUTH_REQUEST_EMAIL": "test@example.com",
    "HTTP_X_AUTH_REQUEST_GROUPS": settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS[0],
}


def create_dataset(dataset_id: str, status: Dataset.Status) -> Dataset:
    return Dataset.objects.create(
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
    selected = create_dataset("dataset.selected", initial_status)
    not_selected = create_dataset("dataset.not_selected", initial_status)
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
    draft = create_dataset("dataset.draft", Dataset.Status.DRAFT)
    published = create_dataset("dataset.published", Dataset.Status.PUBLISHED)
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
