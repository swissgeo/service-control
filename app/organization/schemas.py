from ninja import Schema
from schemas import TranslationsSchema


class OrganizationSchema(Schema):
    id: str
    name: str
    name_translations: TranslationsSchema
    acronym: str
    acronym_translations: TranslationsSchema


class OrganizationListSchema(Schema):
    items: list[OrganizationSchema]
