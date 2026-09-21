import pytest

from thesaurus.models import ROOT_CONCEPT_ID, Concept, Thesaurus


@pytest.fixture(name="thesaurus")
def fixture_thesaurus(db):
    thesaurus = Thesaurus(thesaurus_id="thesaurus_id")
    thesaurus.save()

    root = Concept(
        thesaurus=thesaurus,
        concept_id=ROOT_CONCEPT_ID,
        label_de="root de",
        label_fr="root fr",
        label_en="root en",
        label_it="root it",
        label_rm="root rm",
    )
    root.save()

    parent = Concept(
        thesaurus=thesaurus,
        parent=root,
        concept_id="parent",
        label_de="parent de",
        label_fr="parent fr",
        label_en="parent en",
        label_it="parent it",
        label_rm="parent rm",
    )
    parent.save()

    Concept(
        thesaurus=thesaurus,
        parent=parent,
        concept_id="child",
        label_de="child de",
        label_fr="child fr",
        label_en="child en",
        label_it="child it",
        label_rm="child rm",
    ).save()

    return thesaurus


def test_get_thesaurus_returns_404_for_nonexisting_thesaurus(client, db):
    response = client.get("/api/v1/thesauri/2")

    assert response.status_code == 404
    assert response.json() == {"code": 404, "description": "Resource not found"}


def test_get_thesaurus_returns_existing_thesaurus_with_default_language(thesaurus, client):
    response = client.get(f"/api/v1/thesauri/{thesaurus.thesaurus_id}")

    assert response.status_code == 200
    assert response.json() == [
        {
            "concept_id": "parent",
            "label": "parent en",
            "label_translations": {
                "de": "parent de",
                "fr": "parent fr",
                "en": "parent en",
                "it": "parent it",
                "rm": "parent rm",
            },
            "children": [
                {
                    "concept_id": "child",
                    "label": "child en",
                    "label_translations": {
                        "de": "child de",
                        "fr": "child fr",
                        "en": "child en",
                        "it": "child it",
                        "rm": "child rm",
                    },
                    "children": [],
                }
            ],
        }
    ]


def test_get_thesaurus_returns_thesaurus_with_language_from_query(thesaurus, client):
    response = client.get(f"/api/v1/thesauri/{thesaurus.thesaurus_id}?lang=de")

    assert response.status_code == 200
    assert response.json() == [
        {
            "concept_id": "parent",
            "label": "parent de",
            "label_translations": {
                "de": "parent de",
                "fr": "parent fr",
                "en": "parent en",
                "it": "parent it",
                "rm": "parent rm",
            },
            "children": [
                {
                    "concept_id": "child",
                    "label": "child de",
                    "label_translations": {
                        "de": "child de",
                        "fr": "child fr",
                        "en": "child en",
                        "it": "child it",
                        "rm": "child rm",
                    },
                    "children": [],
                }
            ],
        }
    ]


def test_get_thesaurus_returns_thesaurus_with_language_from_header(thesaurus, client):
    response = client.get(
        f"/api/v1/thesauri/{thesaurus.thesaurus_id}",
        headers={"Accept-Language": "de"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "concept_id": "parent",
            "label": "parent de",
            "label_translations": {
                "de": "parent de",
                "fr": "parent fr",
                "en": "parent en",
                "it": "parent it",
                "rm": "parent rm",
            },
            "children": [
                {
                    "concept_id": "child",
                    "label": "child de",
                    "label_translations": {
                        "de": "child de",
                        "fr": "child fr",
                        "en": "child en",
                        "it": "child it",
                        "rm": "child rm",
                    },
                    "children": [],
                }
            ],
        }
    ]


def test_get_thesaurus_skips_translations_that_are_not_available(thesaurus, client):
    for concept in thesaurus.concept_set.all():
        concept.label_it = None
        concept.save()

    response = client.get(f"/api/v1/thesauri/{thesaurus.thesaurus_id}")

    assert response.status_code == 200
    assert response.json() == [
        {
            "concept_id": "parent",
            "label": "parent en",
            "label_translations": {
                "de": "parent de",
                "fr": "parent fr",
                "en": "parent en",
                "rm": "parent rm",
            },
            "children": [
                {
                    "concept_id": "child",
                    "label": "child en",
                    "label_translations": {
                        "de": "child de",
                        "fr": "child fr",
                        "en": "child en",
                        "rm": "child rm",
                    },
                    "children": [],
                }
            ],
        }
    ]
