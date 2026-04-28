from decimal import Decimal  # noqa:TC003
from typing import Any, Self

from boto3.dynamodb.types import TypeDeserializer
from pydantic import BaseModel, ConfigDict, Field


class ParsingError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


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
        deserializer = TypeDeserializer()
        parsed_data: dict[str, Any] = {}
        for field_name in cls.model_fields:
            if field_name not in item:
                raise ParsingError(f"Missing field '{field_name}' in DynamoDB item")
            dynamo_value = item[field_name]
            try:
                parsed_data[field_name] = deserializer.deserialize(dynamo_value)
            except Exception as e:
                raise ParsingError(
                    f"Error parsing field '{field_name}' with value '{dynamo_value}'"
                ) from e

        return cls(**parsed_data)


class OrganizationImport(DynamoDBParsableModel):
    provider_id: str = Field(serialization_alias="organization_id")
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
    geocat_id: str
    _legacy_id: int


class LayersJSImport(DynamoDBParsableModel):
    layer_id: str
    bod_layer_id: str | None = None
    topics: str | None = None
    chargeable: bool | None = None
    staging: str | None = None
    server_layername: str | None = None
    attribution: str | None = None
    layertype: str | None = None
    opacity: Decimal | None = None
    minresolution: Decimal | None = None
    maxresolution: Decimal | None = None
    extent: list[Decimal] | None = None
    backgroundlayer: bool | None = None
    tooltip: bool | None = None
    searchable: bool | None = None
    timeenabled: bool | None = None
    haslegend: bool | None = None
    singletile: bool | None = None
    highlightable: bool | None = None
    wms_layers: str | None = None
    time_behaviour: str | None = None
    image_format: str | None = None
    tilematrix_resolution_max: Decimal | None = None
    timestamps: list[str] | None = None
    parentlayerid: str | None = None
    sublayersids: list[str] | None = None
    time_get_parameter: str | None = None
    time_format: str | None = None
    wms_gutter: int | None = None
    sphinx_index: str | None = None
    geojson_url_de: str | None = None
    geojson_url_fr: str | None = None
    geojson_url_it: str | None = None
    geojson_url_en: str | None = None
    geojson_url_rm: str | None = None
    geojson_update_delay: int | None = None
    srid: str | None = None


# https://github.com/geoadmin/service-control/blob/develop/app/distributions/export_models.py
class Keyword(DynamoDBParsableModel):
    type: str | None
    thesaurus_id: str | None
    thesaurus_url: str | None
    thesaurus_date: str | None
    concept: str | None
    translation_de: str | None
    translation_fr: str | None
    translation_en: str | None
    translation_it: str | None
    translation_rm: str | None


class KeywordList(DynamoDBParsableModel):
    dataset_id: str
    geocat_id: str
    keywords: list[Keyword]


class OnlineResource(BaseModel):
    url: str | None
    url_de: str | None
    url_fr: str | None
    url_en: str | None
    url_it: str | None
    url_rm: str | None
    protocol: str | None
    name_de: str | None
    name_fr: str | None
    name_en: str | None
    name_it: str | None
    name_rm: str | None
    description_de: str | None
    description_fr: str | None
    description_en: str | None
    description_it: str | None
    description_rm: str | None
    function: str | None


class Contact(BaseModel):
    role: str | None
    org_name: str | None
    org_name_de: str | None
    org_name_fr: str | None
    org_name_en: str | None
    org_name_it: str | None
    org_name_rm: str | None
    org_acronym: str | None
    org_acronym_de: str | None
    org_acronym_fr: str | None
    org_acronym_en: str | None
    org_acronym_it: str | None
    org_acronym_rm: str | None
    position_name_de: str | None
    position_name_fr: str | None
    position_name_en: str | None
    position_name_it: str | None
    position_name_rm: str | None
    contact_voice: str | None
    contact_facsimile: str | None
    contact_sms: str | None
    contact_city: str | None
    contact_administrative_area: str | None
    contact_postal_code: str | None
    contact_country: str | None
    contact_electronic_mail_addresses: list[str]
    contact_delivery_point: str | None
    online_resources: list[OnlineResource]


class ContactList(DynamoDBParsableModel):
    dataset_id: str
    geocat_id: str
    contacts: list[Contact]
