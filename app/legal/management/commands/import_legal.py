import json
from json import loads
from pathlib import Path
from typing import Any

from requests import get

from django.core.management.base import CommandParser

from legal.models import GeopoliticalEntity
from utils.command import CustomBaseCommand


class Command(CustomBaseCommand):
    """Import data from geobasisdaten.ch."""

    help = "Import data from geobasisdaten.ch."

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)

        parser.add_argument(
            "--endpoint",
            default="https://api.geobasisdaten.ch/api/v1/corp/?format=json",
            help="Geopolitical entities endpoint URL.",
        )
        parser.add_argument(
            "--directory",
            help=(
                "Path to a local folder containing the response of the legal information (JSON) "
                "Useful for local development."
            ),
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default="60",
            help="Timeout when calling geopolitical entities (JSON) endpoint",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        """Main entry point of command."""

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options, default=str)}")

        entities = {}
        entities = self.get_service(
            options["endpoint"],
            options["directory"],
            options["timeout"],
        )

        entities = self.sanitize_json_response(entities)

        self.import_entities(entities)

    def get_service(
        self,
        endpoint: str,
        directory: str,
        timeout: int,
    ) -> list[dict]:
        """
        Download the geopolitical entities as JSON from the provided endpoint URL or load the from
        the given directory
        """

        result = []

        if directory:
            path = Path(directory)
            if not path.exists():
                self.print_error(f"{directory} does not exist")
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
                url = f"{endpoint}"
                response = get(url, timeout=timeout)
                response.raise_for_status()
                result = response.json()
            except Exception as e:  # noqa: BLE001
                self.print_error(f"Failed to retrieve geopolitical entities: {e}")

        return result

    def import_entities(self, entities: list[dict]) -> None:

        self.print_success("Start importing geopolitical entities")

        metrics = {"entities.created": 0, "entities.updated": 0}

        # import non existing entities
        created = self.add_new_entries(entities)
        metrics["entities.created"] += created

        # Update existing entities
        updated = self.update_existing_entries(entities)
        metrics["entities.updated"] += updated

        self.print_success(f"Geopolitical entities import complete. Metrics: {metrics}")

    def add_new_entries(self, entities: list[dict]) -> int:
        """
        Checks if an entry of the fetched api data exists already in the db.
        If not it creates a new entry
        """

        created = 0

        # fetch all existing entries from the db
        existing_entity_objects = GeopoliticalEntity.objects.all()
        existing_entities = {
            entity.geopolitical_entity_id: entity for entity in existing_entity_objects
        }

        # iterate over api data and check for changes
        created_entries = []
        for entity in entities:
            created_entry = GeopoliticalEntity(
                geopolitical_entity_id=str(entity["id"]),
                type=self.map_levels(entity["level"]),
                name_de=entity["nameDe"],
                name_fr=entity["nameFr"],
                name_it=entity["nameIt"],
                name_rm=entity["nameRm"],
                abbr=entity["abbr"],
            )

            if created_entry.geopolitical_entity_id not in existing_entities:
                created_entries.append(created_entry)
                created += 1
                self.print(f"Added entity: {created_entry.geopolitical_entity_id}")

        GeopoliticalEntity.objects.bulk_create(created_entries)

        return created

    def update_existing_entries(self, entities: list[dict]) -> int:
        """
        Checks if an entry of the fetched api data exists already in the db.
        If the entry already exists it checks if the data attribute values has changed
        and apply the change if necessary to the db data. Also adds the parent
        if it exists and is missing
        """

        updated = 0

        # fetch all existing entries from the db
        existing_entity_objects = GeopoliticalEntity.objects.all()
        existing_entities = {
            entity.geopolitical_entity_id: entity for entity in existing_entity_objects
        }

        # iterate over api data and check for changes
        for entity in entities:
            created_entry = GeopoliticalEntity(
                geopolitical_entity_id=str(entity["id"]),
                type=self.map_levels(entity["level"]),
                name_de=entity["nameDe"],
                name_fr=entity["nameFr"],
                name_it=entity["nameIt"],
                name_rm=entity["nameRm"],
                abbr=entity["abbr"],
            )

            created_entity_id = created_entry.geopolitical_entity_id
            if created_entity_id not in existing_entities:
                continue

            existing_entity = existing_entities[created_entity_id]

            # alle necessary fields for comparison
            fields_to_update = ["type", "name_de", "name_fr", "name_it", "name_rm", "abbr"]
            changed_fields = []

            # special check for entity parent
            entity_parent = None
            if entity["parent"] is not None:
                entity_parent = str(entity["parent"])

            if getattr(existing_entity.parent, "geopolitical_entity_id", None) != entity_parent:
                if entity_parent is None:
                    existing_entity.parent = None
                    self.print(
                        f"Parent removed for entity: {existing_entity.geopolitical_entity_id}"
                    )
                else:
                    existing_entity.parent = existing_entities.get(entity_parent)
                    self.print(
                        f"Parent added/updated for entity: {existing_entity.geopolitical_entity_id}"
                    )

                changed_fields.append("parent")
            else:
                self.print(f"No Parent exists for entity: {existing_entity.geopolitical_entity_id}")

            # check for all other attribute values
            for field in fields_to_update:
                if getattr(existing_entity, field) != getattr(created_entry, field):
                    setattr(existing_entity, field, getattr(created_entry, field))
                    changed_fields.append(field)

            # save change if there was one
            if changed_fields:
                changed_fields.append("updated_at")
                existing_entity.save(update_fields=changed_fields)
                updated += 1
                self.print(f"Updated entity: {existing_entity.geopolitical_entity_id}")

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

    def sanitize_json_response(self, entities: list[dict]) -> list[dict]:
        """Remove any leading and trailing white spaces for all values of the received JSON"""
        if not isinstance(entities, list):
            self.print_error("Entities arg was not a list")
            return entities

        for entity in entities:
            keys = entity.keys()
            for key in keys:
                if isinstance(entity[key], str):
                    entity[key] = entity[key].strip()

        return entities
