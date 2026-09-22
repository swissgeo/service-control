import pytest

from thesaurus.models import ROOT_CONCEPT_ID, Concept, Thesaurus


@pytest.fixture(name="thesaurus")
def fixture_thesaurus(db):
    thesaurus = Thesaurus(thesaurus_id="mythesaurus")
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
        concept_id="parent_b",
        label_de="parent b de",
        label_fr="parent b fr",
        label_en="parent b en",
        label_it="parent b it",
        label_rm="parent b rm",
        order="B",
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

    Concept(
        thesaurus=thesaurus,
        parent=root,
        concept_id="parent_a",
        label_de="parent a de",
        label_fr="parent a fr",
        label_en="parent a en",
        label_it="parent a it",
        label_rm="parent a rm",
        order="A",
    ).save()

    return thesaurus


def test_get_thesaurus_returns_404_for_nonexisting_thesaurus(client, db):
    response = client.get("/api/v1/thesauri/2")

    assert response.status_code == 404
    assert response.json() == {"code": 404, "description": "Resource not found"}


def test_get_thesaurus_returns_existing_thesaurus_with_default_language(thesaurus, client):
    response = client.get(f"/api/v1/thesauri/{thesaurus.thesaurus_id}")

    assert response.status_code == 200
    assert response.json() == {
        "thesaurus_id": "mythesaurus",
        "concepts": [
            {
                "concept_id": "parent_a",
                "label": "parent a en",
                "label_translations": {
                    "de": "parent a de",
                    "fr": "parent a fr",
                    "en": "parent a en",
                    "it": "parent a it",
                    "rm": "parent a rm",
                },
                "children": [],
            },
            {
                "concept_id": "parent_b",
                "label": "parent b en",
                "label_translations": {
                    "de": "parent b de",
                    "fr": "parent b fr",
                    "en": "parent b en",
                    "it": "parent b it",
                    "rm": "parent b rm",
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
            },
        ],
    }


def test_get_thesaurus_returns_thesaurus_with_language_from_query(thesaurus, client):
    response = client.get(f"/api/v1/thesauri/{thesaurus.thesaurus_id}?lang=de")

    assert response.status_code == 200
    assert response.json() == {
        "thesaurus_id": "mythesaurus",
        "concepts": [
            {
                "concept_id": "parent_a",
                "label": "parent a de",
                "label_translations": {
                    "de": "parent a de",
                    "fr": "parent a fr",
                    "en": "parent a en",
                    "it": "parent a it",
                    "rm": "parent a rm",
                },
                "children": [],
            },
            {
                "concept_id": "parent_b",
                "label": "parent b de",
                "label_translations": {
                    "de": "parent b de",
                    "fr": "parent b fr",
                    "en": "parent b en",
                    "it": "parent b it",
                    "rm": "parent b rm",
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
            },
        ],
    }


def test_get_thesaurus_returns_thesaurus_with_language_from_header(thesaurus, client):
    response = client.get(
        f"/api/v1/thesauri/{thesaurus.thesaurus_id}",
        headers={"Accept-Language": "de"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "thesaurus_id": "mythesaurus",
        "concepts": [
            {
                "concept_id": "parent_a",
                "label": "parent a de",
                "label_translations": {
                    "de": "parent a de",
                    "fr": "parent a fr",
                    "en": "parent a en",
                    "it": "parent a it",
                    "rm": "parent a rm",
                },
                "children": [],
            },
            {
                "concept_id": "parent_b",
                "label": "parent b de",
                "label_translations": {
                    "de": "parent b de",
                    "fr": "parent b fr",
                    "en": "parent b en",
                    "it": "parent b it",
                    "rm": "parent b rm",
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
            },
        ],
    }


def test_get_thesaurus_skips_translations_that_are_not_available(thesaurus, client):
    for concept in thesaurus.concept_set.all():
        concept.label_it = None
        concept.save()

    response = client.get(f"/api/v1/thesauri/{thesaurus.thesaurus_id}")

    assert response.status_code == 200
    assert response.json() == {
        "thesaurus_id": "mythesaurus",
        "concepts": [
            {
                "concept_id": "parent_a",
                "label": "parent a en",
                "label_translations": {
                    "de": "parent a de",
                    "fr": "parent a fr",
                    "en": "parent a en",
                    "rm": "parent a rm",
                },
                "children": [],
            },
            {
                "concept_id": "parent_b",
                "label": "parent b en",
                "label_translations": {
                    "de": "parent b de",
                    "fr": "parent b fr",
                    "en": "parent b en",
                    "rm": "parent b rm",
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
            },
        ],
    }


def test_get_thesaurus_returns_existing_thesaurus_as_jsonld(thesaurus, client):
    response = client.get(f"/api/v1/thesauri/{thesaurus.thesaurus_id}?format=jsonld")

    assert response.status_code == 200
    assert sorted(response.json(), key=lambda x: x["@id"]) == [
        {
            "@id": "https://swissgeo.ch/thesaurus/mythesaurus",
            "@type": ["http://www.w3.org/2004/02/skos/core#ConceptScheme"],
            "http://purl.org/dc/terms/identifier": [{"@value": "mythesaurus"}],
            "http://www.w3.org/2004/02/skos/core#hasTopConcept": [
                {"@id": "https://swissgeo.ch/thesaurus/mythesaurus/concept/parent_a"},
                {"@id": "https://swissgeo.ch/thesaurus/mythesaurus/concept/parent_b"},
            ],
        },
        {
            "@id": "https://swissgeo.ch/thesaurus/mythesaurus/concept/child",
            "@type": ["http://www.w3.org/2004/02/skos/core#Concept"],
            "http://purl.org/dc/terms/identifier": [{"@value": "child"}],
            "http://www.w3.org/2004/02/skos/core#broader": [
                {"@id": "https://swissgeo.ch/thesaurus/mythesaurus/concept/parent_b"}
            ],
            "http://www.w3.org/2004/02/skos/core#inScheme": [
                {"@id": "https://swissgeo.ch/thesaurus/mythesaurus"}
            ],
            "http://www.w3.org/2004/02/skos/core#prefLabel": [
                {"@language": "de", "@value": "child de"},
                {"@language": "fr", "@value": "child fr"},
                {"@language": "it", "@value": "child it"},
                {"@language": "rm", "@value": "child rm"},
                {"@language": "en", "@value": "child en"},
            ],
        },
        {
            "@id": "https://swissgeo.ch/thesaurus/mythesaurus/concept/parent_a",
            "@type": ["http://www.w3.org/2004/02/skos/core#Concept"],
            "http://purl.org/dc/terms/identifier": [{"@value": "parent_a"}],
            "http://www.w3.org/2004/02/skos/core#inScheme": [
                {"@id": "https://swissgeo.ch/thesaurus/mythesaurus"}
            ],
            "http://www.w3.org/2004/02/skos/core#prefLabel": [
                {"@language": "de", "@value": "parent a de"},
                {"@language": "fr", "@value": "parent a fr"},
                {"@language": "it", "@value": "parent a it"},
                {"@language": "rm", "@value": "parent a rm"},
                {"@language": "en", "@value": "parent a en"},
            ],
            "http://www.w3.org/2004/02/skos/core#topConceptOf": [
                {"@id": "https://swissgeo.ch/thesaurus/mythesaurus"}
            ],
            "https://schema.org/position": [{"@value": "A"}],
        },
        {
            "@id": "https://swissgeo.ch/thesaurus/mythesaurus/concept/parent_b",
            "@type": ["http://www.w3.org/2004/02/skos/core#Concept"],
            "http://purl.org/dc/terms/identifier": [{"@value": "parent_b"}],
            "http://www.w3.org/2004/02/skos/core#inScheme": [
                {"@id": "https://swissgeo.ch/thesaurus/mythesaurus"}
            ],
            "http://www.w3.org/2004/02/skos/core#narrower": [
                {"@id": "https://swissgeo.ch/thesaurus/mythesaurus/concept/child"}
            ],
            "http://www.w3.org/2004/02/skos/core#prefLabel": [
                {"@language": "de", "@value": "parent b de"},
                {"@language": "fr", "@value": "parent b fr"},
                {"@language": "it", "@value": "parent b it"},
                {"@language": "rm", "@value": "parent b rm"},
                {"@language": "en", "@value": "parent b en"},
            ],
            "http://www.w3.org/2004/02/skos/core#topConceptOf": [
                {"@id": "https://swissgeo.ch/thesaurus/mythesaurus"}
            ],
            "https://schema.org/position": [{"@value": "B"}],
        },
    ]
