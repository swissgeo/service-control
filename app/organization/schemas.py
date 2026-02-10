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


class CreateOrganizationSchema(Schema):
    id: str
    name_translations: TranslationsSchema
    acronym_translations: TranslationsSchema


class UpdateOrganizationSchema(Schema):
    name_translations: TranslationsSchema
    acronym_translations: TranslationsSchema


class UnitSchema(Schema):
    id: str
    name: str
    name_translations: TranslationsSchema
    organization_id: str


class UnitListSchema(Schema):
    items: list[UnitSchema]


class CreateUnitSchema(Schema):
    id: str
    name_translations: TranslationsSchema
    organization_id: str


class UpdateUnitSchema(Schema):
    name_translations: TranslationsSchema
