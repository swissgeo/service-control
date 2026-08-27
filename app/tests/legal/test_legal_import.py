from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

from legal.management.commands.import_legal import Command
from legal.models import GeopoliticalEntity


@patch("organization.models.Client")
@patch("legal.management.commands.import_legal.get", name="mocks")
def test_new_geopolitical_entitites(mock, client, db):
    mock.return_value.json.return_value = [
        {
            "id": 34481,
            "parent": 32395,
            "level": "corp",
            "bfsNumber": None,
            "parentBfsNumber": 4,
            "filterDisplay": "Korporation  Ursern (UR)",
            "abbr": "KOPORATI",
            "name": " Ursern",
            "nameDe": " Ursern",
            "nameFr": "Corporation d'Ursern",
            "nameIt": "Corporazione di Ursern",
            "nameRm": "Corporaziun d'Ursern",
        },
        {
            "id": 32395,
            "parent": None,
            "level": "canton",
            "bfsNumber": 4,
            "parentBfsNumber": None,
            "filterDisplay": "Kanton Uri",
            "abbr": "UR",
            "name": "Uri",
            "nameDe": "Uri",
            "nameFr": "Uri",
            "nameIt": "Uri",
            "nameRm": "Uri",
        },
    ]

    out = StringIO()
    call_command("import_legal", verbosity=2, stdout=out)
    out = out.getvalue()

    saved_entities = GeopoliticalEntity.objects.all()
    assert len(saved_entities) == 2
    corp_entry = saved_entities.get(geopolitical_entity_id="34481")
    assert corp_entry.type == "corporal"
    assert corp_entry.parent == saved_entities.get(geopolitical_entity_id="32395")
    assert (
        "Geopolitical entities import complete. Metrics: "
        "{'entities.created': 2, 'entities.updated': 1}" in out
    )


@patch("organization.models.Client")
@patch("legal.management.commands.import_legal.get", name="mock")
def test_update_geopolitical_entitites(mock, client, db):
    mock.return_value.json.return_value = [
        {
            "id": 34481,
            "parent": 32395,
            "level": "region",
            "bfsNumber": None,
            "parentBfsNumber": 4,
            "filterDisplay": "Korporation  Ursern (UR)",
            "abbr": "KOPORATI",
            "name": " Ursern",
            "nameDe": " Ursern",
            "nameFr": "Corporation d'Ursern",
            "nameIt": "Corporazione di Ursern",
            "nameRm": "Corporaziun d'Ursern",
        },
        {
            "id": 32395,
            "parent": None,
            "level": "canton",
            "bfsNumber": 4,
            "parentBfsNumber": None,
            "filterDisplay": "Kanton Uri",
            "abbr": "UR",
            "name": "Uri",
            "nameDe": "Uri",
            "nameFr": "Uri",
            "nameIt": "Uri",
            "nameRm": "Uri",
        },
    ]

    GeopoliticalEntity(
        geopolitical_entity_id="34481",
        type="corporal",
        name_de="Ursern",
        name_fr="Corporation d'Ursern",
        name_it="Corporazione di Ursern",
        name_rm="Corporaziun d'Ursern",
        abbr="KOPORATI",
        parent=None,
    ).save()

    saved_entities = GeopoliticalEntity.objects.all()
    assert len(saved_entities) == 1
    corp_entry = saved_entities.get(geopolitical_entity_id="34481")
    assert corp_entry.parent is None

    out = StringIO()
    call_command("import_legal", verbosity=2, stdout=out)
    out = out.getvalue()

    saved_entities = GeopoliticalEntity.objects.all()
    assert len(saved_entities) == 2
    corp_entry = saved_entities.get(geopolitical_entity_id="34481")
    assert corp_entry.type == "districtal"
    assert corp_entry.parent == saved_entities.get(geopolitical_entity_id="32395")
    assert (
        "Geopolitical entities import complete. Metrics: "
        "{'entities.created': 1, 'entities.updated': 1}" in out
    )


@patch("organization.models.Client")
@patch("legal.management.commands.import_legal.get", name="mock")
def test_geopolitical_entitites_parent_not_existing(mock, client, db):
    mock.return_value.json.return_value = [
        {
            "id": 34481,
            "parent": 32395,
            "level": "corp",
            "bfsNumber": None,
            "parentBfsNumber": 4,
            "filterDisplay": "Korporation  Ursern (UR)",
            "abbr": "KOPORATI",
            "name": " Ursern",
            "nameDe": " Ursern",
            "nameFr": "Corporation d'Ursern",
            "nameIt": "Corporazione di Ursern",
            "nameRm": "Corporaziun d'Ursern",
        },
        {
            "id": 32395,
            "parent": 1,
            "level": "canton",
            "bfsNumber": 4,
            "parentBfsNumber": None,
            "filterDisplay": "Kanton Uri",
            "abbr": "UR",
            "name": "Uri",
            "nameDe": "Uri",
            "nameFr": "Uri",
            "nameIt": "Uri",
            "nameRm": "Uri",
        },
    ]

    out = StringIO()
    call_command("import_legal", verbosity=2, stdout=out)
    out = out.getvalue()

    saved_entities = GeopoliticalEntity.objects.all()
    assert len(saved_entities) == 2
    corp_entry = saved_entities.get(geopolitical_entity_id="34481")
    assert corp_entry.type == "corporal"
    assert corp_entry.parent == saved_entities.get(geopolitical_entity_id="32395")
    corp_entry = saved_entities.get(geopolitical_entity_id="32395")
    assert corp_entry.type == "cantonal"
    assert corp_entry.parent is None
    assert (
        "Geopolitical entities import complete. Metrics: "
        "{'entities.created': 2, 'entities.updated': 2}" in out
    )


def test_sanitize_json_response():
    json_list = [
        {
            "id": 32395,
            "parent": None,
            "level": "canton",
            "bfsNumber": 4,
            "parentBfsNumber": None,
            "filterDisplay": "Kanton Uri",
            "abbr": " UR",
            "name": " Uri ",
            "nameDe": "Uri ",
            "nameFr": "Uri   ",
            "nameIt": "   Uri",
            "nameRm": "   Uri   ",
        }
    ]

    sanitized_json = Command().sanitize_json_response(json_list)
    assert sanitized_json[0]["abbr"] == "UR"
    assert sanitized_json[0]["name"] == "Uri"
    assert sanitized_json[0]["nameDe"] == "Uri"
    assert sanitized_json[0]["nameFr"] == "Uri"
    assert sanitized_json[0]["nameIt"] == "Uri"
    assert sanitized_json[0]["nameRm"] == "Uri"


def test_map_levels():
    assert Command().map_levels("region") == GeopoliticalEntity.Level.DISTRICTAL
    assert Command().map_levels("county") == GeopoliticalEntity.Level.DISTRICTAL
    assert Command().map_levels("federal") == GeopoliticalEntity.Level.FEDERAL
    assert Command().map_levels("") == GeopoliticalEntity.Level.COMMUNAL
    assert Command().map_levels("nonsense") == GeopoliticalEntity.Level.COMMUNAL
