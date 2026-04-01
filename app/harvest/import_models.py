from decimal import Decimal
from typing import Any, Self

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
        parsed_data: dict[str, Any] = {}
        for field_name in cls.model_fields:
            if field_name not in item:
                raise ParsingError(f"Missing field '{field_name}' in DynamoDB item")
            dynamo_value = item[field_name]
            try:
                parsed_data[field_name] = cls.handle_item(dynamo_value)
            except Exception as e:
                raise ParsingError(
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
        elif type_key == "M":
            conv = cls.handle_M(value)
        elif type_key == "NULL":
            conv = None
        elif type_key == "BOOL":
            conv = cls.handle_BOOL(value)
        else:
            raise ValueError(f"Unsupported DynamoDB type '{type_key}' (value: '{value}'")

        return conv

    @classmethod
    def handle_S(cls, value: str) -> str:  # noqa: N802
        return value

    @classmethod
    def handle_N(cls, value: Any) -> Decimal:  # noqa: N802
        """Convert DynamoDB N-type

        We convert all N-type fields to Decimal in a first step.
        Decimal input values are then automatically converted to
        int/float when constructing pydantic objects, as long as
        the number can be converted to the target type, so
        - Decimal('3.5) can be casted to float, but not to int
        - Decimal('3') can be casted to int and to float
        """
        return Decimal(value)

    @classmethod
    def handle_L(cls, value: list) -> list:  # noqa: N802
        return [cls.handle_item(item) for item in value]

    @classmethod
    def handle_M(cls, value: dict) -> dict:  # noqa: N802
        return {key: cls.handle_item(item) for key, item in value.items()}

    @classmethod
    def handle_BOOL(cls, value: bool) -> bool:  # noqa: N802
        return value


class OrganisationImport(DynamoDBParsableModel):
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
