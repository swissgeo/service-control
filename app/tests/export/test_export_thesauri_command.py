from io import StringIO
from json import loads
from unittest.mock import patch

from django.core.management import call_command

import pytest

from thesaurus.models import ECH0166_THESAURUS_ID, ROOT_CONCEPT_ID, Concept, Thesaurus


def extract_put_object(session):
    result = []
    for call in session.mock_calls:
        if "put_object" in str(call):
            kwargs = call.kwargs.copy()
            kwargs["Body"] = loads(kwargs["Body"])
            result.append(kwargs)
    return result


def extract_delete_objects(session):
    return [call.kwargs for call in session.mock_calls if "delete_objects" in str(call)]


@pytest.fixture(name="thesaurus")
def fixture_thesaurus(db):
    thesaurus = Thesaurus(thesaurus_id=ECH0166_THESAURUS_ID)
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


@patch("export.management.commands.export_thesauri.Session")
def test_command_exports_thesaurus(session, db, thesaurus):
    out = StringIO()
    call_command("export_thesauri", verbosity=2, stdout=out)
    out = out.getvalue()

    assert "ech0166 to api/thesauri/ech0166.de.json" in out
    assert "ech0166 to api/thesauri/ech0166.fr.json" in out
    assert "ech0166 to api/thesauri/ech0166.it.json" in out
    assert "ech0166 to api/thesauri/ech0166.rm.json" in out
    assert "ech0166 to api/thesauri/ech0166.en.json" in out
    assert "ech0166 to api/thesauri/ech0166.json" in out
    assert "Exported 6 objects to static-thesauri-dev-swissgeo" in out

    result = extract_put_object(session)
    assert len(result) == 6
    assert {
        "Bucket": "static-thesauri-dev-swissgeo",
        "Key": "api/thesauri/ech0166.de.json",
        "Body": {
            "thesaurus_id": "ech0166",
            "concepts": [
                {"concept_id": "parent_a", "label": "parent a de", "children": []},
                {
                    "concept_id": "parent_b",
                    "label": "parent b de",
                    "children": [{"concept_id": "child", "label": "child de", "children": []}],
                },
            ],
        },
        "ContentType": "application/json",
    } in result
    assert {
        "Bucket": "static-thesauri-dev-swissgeo",
        "Key": "api/thesauri/ech0166.fr.json",
        "Body": {
            "thesaurus_id": "ech0166",
            "concepts": [
                {"concept_id": "parent_a", "label": "parent a fr", "children": []},
                {
                    "concept_id": "parent_b",
                    "label": "parent b fr",
                    "children": [{"concept_id": "child", "label": "child fr", "children": []}],
                },
            ],
        },
        "ContentType": "application/json",
    } in result
    assert {
        "Bucket": "static-thesauri-dev-swissgeo",
        "Key": "api/thesauri/ech0166.it.json",
        "Body": {
            "thesaurus_id": "ech0166",
            "concepts": [
                {"concept_id": "parent_a", "label": "parent a it", "children": []},
                {
                    "concept_id": "parent_b",
                    "label": "parent b it",
                    "children": [{"concept_id": "child", "label": "child it", "children": []}],
                },
            ],
        },
        "ContentType": "application/json",
    } in result
    assert {
        "Bucket": "static-thesauri-dev-swissgeo",
        "Key": "api/thesauri/ech0166.rm.json",
        "Body": {
            "thesaurus_id": "ech0166",
            "concepts": [
                {"concept_id": "parent_a", "label": "parent a rm", "children": []},
                {
                    "concept_id": "parent_b",
                    "label": "parent b rm",
                    "children": [{"concept_id": "child", "label": "child rm", "children": []}],
                },
            ],
        },
        "ContentType": "application/json",
    } in result
    assert {
        "Bucket": "static-thesauri-dev-swissgeo",
        "Key": "api/thesauri/ech0166.en.json",
        "Body": {
            "thesaurus_id": "ech0166",
            "concepts": [
                {"concept_id": "parent_a", "label": "parent a en", "children": []},
                {
                    "concept_id": "parent_b",
                    "label": "parent b en",
                    "children": [{"concept_id": "child", "label": "child en", "children": []}],
                },
            ],
        },
        "ContentType": "application/json",
    } in result
    # skip testing JSON-LD as is not serialized deterministic


@patch("export.management.commands.export_thesauri.Session")
def test_command_exports_thesauri_dry(session, db, thesaurus):
    out = StringIO()
    call_command("export_thesauri", dry_run=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "ech0166 to api/thesauri/ech0166.de.json" in out
    assert "ech0166 to api/thesauri/ech0166.fr.json" in out
    assert "ech0166 to api/thesauri/ech0166.it.json" in out
    assert "ech0166 to api/thesauri/ech0166.rm.json" in out
    assert "ech0166 to api/thesauri/ech0166.en.json" in out
    assert "ech0166 to api/thesauri/ech0166.json" in out
    assert "Exported 6 objects to static-thesauri-dev-swissgeo" in out

    assert "DRY RUN" in out

    result = extract_put_object(session)
    assert result == []


@patch("export.management.commands.export_thesauri.Session")
def test_command_skips_non_ech_thesauri(session, db, thesaurus):
    thesaurus.thesaurus_id = "foo"
    thesaurus.save()

    out = StringIO()
    call_command("export_thesauri", dry_run=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Exported 0 objects to static-thesauri-dev-swissgeo" in out

    result = extract_put_object(session)
    assert result == []


@patch("export.management.commands.export_thesauri.Session")
def test_command_cleans_thesauri(session, db):
    s3 = session.return_value.client.return_value
    s3.list_objects_v2.side_effect = [
        {"Contents": [{"Key": "a"}], "NextContinuationToken": "tok"},
        {"Contents": [{"Key": "b"}]},
    ]

    out = StringIO()
    call_command(
        "export_thesauri",
        "--verbosity",
        "2",
        "clean",
        stdout=out,
    )
    out = out.getvalue()

    assert "Deleted total of 2 objects" in out

    result = extract_delete_objects(session)
    assert result == [
        {"Bucket": "static-thesauri-dev-swissgeo", "Delete": {"Objects": [{"Key": "a"}]}},
        {"Bucket": "static-thesauri-dev-swissgeo", "Delete": {"Objects": [{"Key": "b"}]}},
    ]
