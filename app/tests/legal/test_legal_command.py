from io import StringIO
from json import dumps

from django.core.management import call_command


def test_legal_command_creates_entities_from_file(client, db, tmp_path):
    file = tmp_path / "geopolitical_entities.json"
    file.write_text(
        dumps(
            [
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
                }
            ]
        )
    )

    out = StringIO()
    call_command(
        "import_legal",
        directory=tmp_path,
        stdout=out,
    )
    out = out.getvalue()

    assert (
        "Geopolitical entities import complete. Metrics: "
        "{'entities.created': 1, 'entities.updated': 1}" in out
    )


def test_legal_command_file_not_existing(client, db, tmp_path):

    err = StringIO()
    call_command(
        "import_legal",
        directory=tmp_path,
        stderr=err,
    )
    err = err.getvalue()

    assert f"Failed to load file {tmp_path}" in err


def test_legal_command_path_not_existing(client, db):

    err = StringIO()
    call_command(
        "import_legal",
        directory="testpath",
        stderr=err,
    )
    err = err.getvalue()

    assert "testpath does not exist" in err
