from io import StringIO
from json import dumps
from unittest.mock import patch

from django.core.management import call_command


@patch("organization.models.Client")
def test_command_creates_organization_from_file(client, db, tmp_path):
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
        geopolitical_entities_directory=tmp_path,
        stdout=out,
    )
    out = out.getvalue()

    assert (
        "Geopolitical entities import complete. Metrics: "
        "{'entities.created': 1, 'entities.updated': 1}" in out
    )
