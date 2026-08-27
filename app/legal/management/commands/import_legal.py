import json
from json import loads
from pathlib import Path
from typing import Any

from requests import get

from django.core.management.base import CommandParser
from django.utils import timezone

from legal.models import GeopoliticalEntity
from utils.command import CustomBaseCommand


class Command(CustomBaseCommand):
    """Import data from geobasisdaten.ch."""

    help = "Import data from geobasisdaten.ch."

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)

        parser.add_argument(
            "--geopolitical-entities-endpoint",
            default="https://api.geobasisdaten.ch/api/v1/corp/?format=json",
            help="Geopolitical Entities endpoint URL.",
        )
        parser.add_argument(
            "--geopolitical-entities-directory",
            help=(
                "Path to a local folder containing the response of the legal information (JSON) "
                "Useful for local development."
            ),
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default="60",
            help="Timeout when calling services information (JSON) endpoint",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        """Main entry point of command."""

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options, default=str)}")

        geopolitical_entities = {}
        geopolitical_entities = self.get_service(
            options["geopolitical_entities_endpoint"],
            options["geopolitical_entities_directory"],
            options["timeout"],
        )

        geopolitical_entities = self.sanitize_json_response(geopolitical_entities)

        self.import_geopolitical_entitites(geopolitical_entities)

    def get_service(
        self,
        geopolitical_entities_endpoint: str,
        geopolitical_entities_directory: str,
        timeout: int,
    ) -> list[dict]:
        """
        Download the service information as JSON from the provided endpoint URL or load the from
        the given directory
        """

        result = []

        if geopolitical_entities_directory:
            path = Path(geopolitical_entities_directory)
            if not path.exists():
                self.print_error(f"{geopolitical_entities_directory} does not exist")
                return []

            filename = path / "geopolitical_entities.json"
            try:
                with open(filename) as file:
                    result = loads(file.read())
            except Exception as e:  # noqa: BLE001
                self.print_error(f"Failed to load file {filename}: {e}")
                return []
        else:
            try:
                url = f"{geopolitical_entities_endpoint}"
                response = get(url, timeout=timeout)
                response.raise_for_status()
                result = response.json()
            except Exception as e:  # noqa: BLE001
                self.print_error(f"Failed to retreive geopolitical entities: {e}")

        return result

    def import_geopolitical_entitites(self, geopolitical_entities: list[dict]) -> None:

        self.print_success("Start importing geopolitical entities")

        metrics = {"entities.created": 0, "entities.updated": 0}

        "Import non existing entities"
        created = self.add_new_entries(geopolitical_entities)
        metrics["entities.created"] += created

        "Update existing entitites"
        updated = self.update_existing_entries(geopolitical_entities)
        metrics["entities.updated"] += updated

        self.print_success(f"Geopolitical entities import complete. Metrics: {metrics}")

    def add_new_entries(self, geopolitical_entities: list[dict]) -> int:
        """
        Checks if an entry of the fetched api data exists already in the db.
        If not it creates a new entry
        """

        created = 0

        # fetch all existing entries from the db
        existing_geopolitical_entity_objects = GeopoliticalEntity.objects.all()
        existing_geopolitical_entities = {
            entity.geopolitical_entity_id: entity for entity in existing_geopolitical_entity_objects
        }

        # iterate over api data and check for changes
        created_entries = []
        for geopolitical_entity in geopolitical_entities:
            created_entry = GeopoliticalEntity(
                geopolitical_entity_id=geopolitical_entity["id"],
                type=self.map_levels(geopolitical_entity["level"]),
                name_de=geopolitical_entity["nameDe"],
                name_fr=geopolitical_entity["nameFr"],
                name_it=geopolitical_entity["nameIt"],
                name_rm=geopolitical_entity["nameRm"],
                abbr=geopolitical_entity["abbr"],
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )

            if str(created_entry.geopolitical_entity_id) not in existing_geopolitical_entities:
                created_entries.append(created_entry)
                created += 1

        GeopoliticalEntity.objects.bulk_create(created_entries)

        return created

    def update_existing_entries(self, geopolitical_entities: list[dict]) -> int:
        """
        Checks if an entry of the fetched api data exists already in the db.
        If the entry already exists it checks if the data attribute values has changed
        and apply the change if necessary to the db data. Also adds the parent
        if it exists and is missing
        """

        updated = 0

        # fetch all existing entries from the db
        existing_geopolitical_entity_objects = GeopoliticalEntity.objects.all()
        existing_geopolitical_entities = {
            entity.geopolitical_entity_id: entity for entity in existing_geopolitical_entity_objects
        }

        # iterate over api data and check for changes
        for geopolitical_entity in geopolitical_entities:
            created_entry = GeopoliticalEntity(
                geopolitical_entity_id=geopolitical_entity["id"],
                type=self.map_levels(geopolitical_entity["level"]),
                name_de=geopolitical_entity["nameDe"],
                name_fr=geopolitical_entity["nameFr"],
                name_it=geopolitical_entity["nameIt"],
                name_rm=geopolitical_entity["nameRm"],
                abbr=geopolitical_entity["abbr"],
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )

            created_geopolitical_entity_id = str(created_entry.geopolitical_entity_id)
            if created_geopolitical_entity_id not in existing_geopolitical_entities:
                continue

            existing_geopolitical_entity = existing_geopolitical_entities[
                created_geopolitical_entity_id
            ]

            # alle necessary fields for comparison
            fields_to_update = ["type", "name_de", "name_fr", "name_it", "name_rm", "abbr"]
            changed_fields = []

            # special check for entity parent
            geopolitical_entity_parent = None
            if geopolitical_entity["parent"] is not None:
                geopolitical_entity_parent = str(geopolitical_entity["parent"])

            if (
                getattr(existing_geopolitical_entity.parent, "geopolitical_entity_id", None)
                != geopolitical_entity_parent
            ):
                if geopolitical_entity_parent is None:
                    existing_geopolitical_entity.parent = None
                else:
                    existing_geopolitical_entity.parent = existing_geopolitical_entities.get(
                        geopolitical_entity_parent
                    )
                changed_fields.append("parent")

            # check for all other attribute values
            for field in fields_to_update:
                if getattr(existing_geopolitical_entity, field) != getattr(created_entry, field):
                    setattr(existing_geopolitical_entity, field, getattr(created_entry, field))
                    changed_fields.append(field)

            # save change if there was one
            if changed_fields:
                existing_geopolitical_entity.updated_at = timezone.now()
                changed_fields.append("updated_at")
                existing_geopolitical_entity.save(update_fields=changed_fields)
                updated += 1

        return updated

    def map_levels(self, input_level: str) -> str:
        match input_level:
            case "region":
                return GeopoliticalEntity.Level.DISTRICTAL
            case "county":
                return GeopoliticalEntity.Level.DISTRICTAL
            case "federal":
                return GeopoliticalEntity.Level.FEDERAL
            case "canton":
                return GeopoliticalEntity.Level.CANTONAL
            case "corp":
                return GeopoliticalEntity.Level.CORPORAL
            case _:
                return GeopoliticalEntity.Level.COMMUNAL

    def sanitize_json_response(self, geopolitical_entities: list[dict]) -> list[dict]:
        for geopolitical_entity in geopolitical_entities:
            keys = geopolitical_entity.keys()
            for key in keys:
                if type(geopolitical_entity[key]) is str:
                    geopolitical_entity[key] = geopolitical_entity[key].strip()

        return geopolitical_entities
