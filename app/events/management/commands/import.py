import json
import pathlib
from typing import Annotated, Any, Literal, Optional, TypeVar

import boto3
import environ
import requests
from botocore.client import Config
from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from tinydb import Query, TinyDB

from django.core.management.base import CommandParser

from config.settings_base import BASE_DIR
from organization.models import Organization
from utils.command import CustomBaseCommand

env = environ.Env()

P = TypeVar("P", bound="DynamoDBParsableModel")


class DynamoDBParsableModel(BaseModel):
    """Base model for parsing DynamoDB items, which are returned in a specific
    format."""

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_dynamodb_item(cls: type[P], item: dict[str, Any]) -> P:
        """Parse a DynamoDB item, which is a dict where each key maps to another
        dict with a single key indicating the type (e.g., 'S' for string) and
        the value.

        For example, an item like {'name': {'S': 'Alice'}, 'age': {'N': '30'}}
        would be parsed into {'name': 'Alice', 'age': 30}.

        This method assumes that all fields in the model are present in the item
        and that their types match. It will raise a ValidationError if parsing
        fails.
        """
        parsed_data: Annotated[dict[str, Any], ""] = dict()
        for field_name, field_info in cls.model_fields.items():
            if field_name not in item:
                raise ValueError(f"Missing field '{field_name}' in DynamoDB item")
            dynamo_value = item[field_name]
            if not isinstance(dynamo_value, dict) or len(dynamo_value) != 1:
                raise ValueError(f"Invalid format for field '{field_name}': {dynamo_value}")
            type_key, value = next(iter(dynamo_value.items()))
            if type_key == "S":
                # special handling for "NONE" strings: convert it to None
                if value == "NONE":
                    parsed_data[field_name] = None
                else:
                    parsed_data[field_name] = value
            elif type_key == "N":
                parsed_data[field_name] = int(value)  # or float(value) if needed
            else:
                raise ValueError(f"Unsupported DynamoDB type '{type_key}' for field '{field_name}'")

        return cls(**parsed_data)


class Command(CustomBaseCommand):
    """Manage OGC API Records Content.

    Currently, this command harvests various sources, merges their content,
    and writes static OGC API Records compliant JSON files to S3

    """

    help = "OAR management"

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
            "--target-env",
            type=str,
            choices=["dev", "int", "prod"],
            default="dev",
            help="Specify the target environment",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Main entry point of command."""
        if env.str("USER") != "geoadmin":
            if options["target_env"] == "dev":
                profile_name = "swisstopo-swissgeo-dev"
            elif options["target_env"] in ["int", "prod"]:
                profile_name = "swisstopo-swissgeo"
            else:
                raise ValueError(f"Invalid target environment: {options['target_env']}")
            self.print(
                f"We're likely running this command locally, so we're using"
                f" the SSO profile {profile_name} to get a session."
            )
            self.session = boto3.Session(profile_name=profile_name)  # pylint: disable=attribute-defined-outside-init
        else:
            self.session = boto3.Session()  # pylint: disable=attribute-defined-outside-init

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:
            self.print(f"Debug: parsed args = {json.dumps(options)}")

        # Handle sub-commands
        if options["organisations"]:
            self.import_organisations(*args, **options)

    # ##########################################################################
    def import_organisations(self, *args: Any, **options: Any) -> None:
        # region Organisations
        self.print_success(f"Importing organisations")

        dynamodb_client = self.session.client("dynamodb", region_name="eu-central-1")
        paginator = dynamodb_client.get_paginator("scan")

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

        for page in paginator.paginate(TableName=f"harvest-providers-{options['target_env']}"):
            for item in page["Items"]:
                try:
                    org = OrganisationImport.from_dynamodb_item(item)
                    self.print_success(f"Parsed organisation: {org.provider_id} - {org.name_de}")
                except Exception as e:
                    self.print_error(f"Failed to parse item: {item}. Error: {e}")

                updated_org = Organization(**org.model_dump(by_alias=True))

                # Overwrite existing organisation if provider_id already exists,
                # otherwise create a new one
                if Organization.objects.filter(organization_id=org.provider_id).exists():
                    self.print(
                        f"Organisation with organization_id {org.provider_id} already exists, updating."
                    )
                    existing_org = Organization.objects.get(organization_id=org.provider_id)
                    updated_org.id = existing_org.id  # Preserve the existing ID

                updated_org.save()
        # endregion
