import json
from typing import TYPE_CHECKING, Annotated, Any, Self, TypeVar

import boto3
import environ
from pydantic import BaseModel, ConfigDict, Field

from dataset.models import Dataset
from organization.models import Organization
from utils.command import CustomBaseCommand

if TYPE_CHECKING:
    from django.core.management.base import CommandParser

env = environ.Env()


class DynamoDBParsableModel(BaseModel):
    """Base model for parsing DynamoDB items, which are returned in a specific
    format."""

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_dynamodb_item(cls, item: dict[str, Any]) -> Self:
        """Parse a DynamoDB item, which is a dict where each key maps to another
        dict with a single key indicating the type (e.g., 'S' for string) and
        the value.

        For example, an item like {'name': {'S': 'Alice'}, 'age': {'N': '30'}}
        would be parsed into {'name': 'Alice', 'age': 30}.

        This method assumes that all fields in the model are present in the item
        and that their types match. It will raise a ValidationError if parsing
        fails.
        """
        parsed_data: dict[str, Any] = {}
        for field_name in cls.model_fields:
            if field_name not in item:
                raise ValueError(f"Missing field '{field_name}' in DynamoDB item")
            dynamo_value = item[field_name]
            try:
                parsed_data[field_name] = cls.handle_item(dynamo_value)
            except Exception as e:
                raise ValueError(
                    f"Error parsing field '{field_name}' with value '{dynamo_value}'"
                ) from e

        return cls(**parsed_data)

    @classmethod
    def handle_item(cls, item: dict) -> Any:
        if not isinstance(item, dict) or len(item) != 1:
            raise TypeError(f"Invalid item type {type(item)}, expecting `dict`")
        if len(item) != 1:
            raise ValueError(f"I can only handle items with 1 key/value pair, got {len(item)}")
        type_key, value = next(iter(item.items()))
        if type_key == "S":
            conv = cls.handle_S(value)
        elif type_key == "N":
            conv = cls.handle_N(value)
        elif type_key == "L":
            conv = cls.handle_L(value)
        elif type_key == "NULL":
            conv = None
        else:
            raise ValueError(f"Unsupported DynamoDB type '{type_key}' (value: '{value}'")

        return conv

    @classmethod
    def handle_S(cls, value: Any) -> str | None:  # noqa: N802
        return value

    @classmethod
    def handle_N(cls, value: Any) -> int | None:  # noqa: N802
        return int(value)  # or float(value) if needed

    @classmethod
    def handle_L(cls, value: list) -> list | None:  # noqa: N802
        return [cls.handle_item(item) for item in value]


class OrganisationImport(DynamoDBParsableModel):
    provider_id: str = Field(serialization_alias="organization_id")
    created: str
    updated: str
    name_de: str
    name_fr: str
    name_en: str
    name_it: str | None
    name_rm: str | None
    acronym_de: str
    acronym_fr: str
    acronym_en: str
    acronym_it: str | None
    acronym_rm: str | None
    _legacy_id: int


class Command(CustomBaseCommand):
    """Import data from DynamoDB harvesting tables.

    This command imports data from DynamoDB harvesting tables. It currently supports importing
    organisations, but can be extended to import other entities in the future.

    """

    help = "Importing data from DynamoDB harvesting tables. "
    "Currently supports importing organisations."

    def add_arguments(self, parser: CommandParser) -> None:
        # Call the base class method to get default arguments defined in the base class
        # (mainly 'logger')
        super().add_arguments(parser)

        # Select entities to import
        parser.add_argument(
            "--organisations",
            action="store_true",
            help="Import organisations",
        )
        parser.add_argument(
            "--datasets",
            action="store_true",
            help="Import datasets",
        )
        parser.add_argument(
            "--target-env",
            type=str,
            choices=["dev", "int", "prod"],
            default="dev",
            help="Specify the target environment",
        )

        parser.add_argument(
            "--profile-name",
            type=str,
            nargs="?",
            default=None,
            help="Specify the profile name (only needed locally)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Main entry point of command."""
        if options["profile_name"]:
            self.session = boto3.Session(profile_name=options["profile_name"])
        else:
            self.session = boto3.Session()

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options)}")

        # Handle sub-commands
        if options["organisations"]:
            self.import_organisations(*args, **options)
        if options["datasets"]:
            self.import_datasets(*args, **options)

    # ##########################################################################
    def import_organisations(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        self.print_success("Importing organisations")

        dynamodb_client = self.session.client("dynamodb", region_name="eu-central-1")
        paginator = dynamodb_client.get_paginator("scan")

        for page in paginator.paginate(TableName=f"harvest-providers-{options['target_env']}"):
            for item in page["Items"]:
                try:
                    import_org = OrganisationImport.from_dynamodb_item(item)
                    self.print_success(
                        f"Parsed organisation: {import_org.provider_id} - {import_org.name_de}"
                    )
                except Exception as e:  # noqa: BLE001
                    self.print_error(f"Failed to parse item: {item}. Error: {e}")

                # check if we have an existing object with the same provider_id
                # if yes, get it from db and update values,
                # if not, create a new object
                try:
                    org = Organization.objects.get(organization_id=import_org.provider_id)
                except Organization.DoesNotExist:
                    self.print(
                        f"Organisation with provider_id {import_org.provider_id} does not exist yet"
                        ", creating a new one."
                    )
                    org = Organization(**import_org.model_dump(by_alias=True))
                else:
                    self.print(
                        f"Organisation with provider_id {import_org.provider_id} already exists, "
                        "updating."
                    )
                    for field in import_org:
                        setattr(org, field[0], field[1])

                org.save()

    # ##########################################################################
    def import_datasets(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        self.print_success("Importing datasets")

        class DatasetImport(DynamoDBParsableModel):
            dataset_id: str
            title_de: str
            title_fr: str
            title_en: str
            title_it: str | None
            title_rm: str | None
            description_de: str
            description_fr: str
            description_en: str
            description_it: str | None
            description_rm: str | None
            attribution: list[str]
            provider: list[str]
            created: str
            updated: str
            geocat_id: str
            _legacy_id: int

        dynamodb_client = self.session.client("dynamodb", region_name="eu-central-1")
        paginator = dynamodb_client.get_paginator("scan")

        for page in paginator.paginate(TableName=f"harvest-datasets-{options['target_env']}"):
            for item in page["Items"]:
                try:
                    import_ds = DatasetImport.from_dynamodb_item(item)
                    self.print_success(
                        f"Parsed dataset: {import_ds.dataset_id} - {import_ds.title_de}"
                    )
                except Exception as e:  # noqa: BLE001
                    self.print_error(f"Failed to parse item: {item}. Error: {e}")

                ds, _ = Dataset.objects.get_or_create(
                    dataset_id=import_ds.dataset_id,
                    defaults={
                        "title_short_de": import_ds.title_de,
                        "title_short_fr": import_ds.title_fr,
                        "title_short_en": import_ds.title_en,
                        "title_short_it": import_ds.title_it,
                        "title_short_rm": import_ds.title_rm,
                        "description_de": import_ds.description_de,
                        "description_fr": import_ds.description_fr,
                        "description_en": import_ds.description_en,
                        "description_it": import_ds.description_it,
                        "description_rm": import_ds.description_rm,
                        "geocat_id": import_ds.geocat_id,
                    },
                )

                ds.title_short_de = import_ds.title_de
                ds.title_short_fr = import_ds.title_fr
                ds.title_short_en = import_ds.title_en
                ds.title_short_it = import_ds.title_it
                ds.title_short_rm = import_ds.title_rm
                ds.description_de = import_ds.description_de
                ds.description_fr = import_ds.description_fr
                ds.description_en = import_ds.description_en
                ds.description_it = import_ds.description_it
                ds.description_rm = import_ds.description_rm
                ds.geocat_id = import_ds.geocat_id

                ds.save()
