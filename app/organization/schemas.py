from typing import TYPE_CHECKING, TypedDict

from ninja import Field, Schema

from organization.models import Organization  # noqa: TC001
from schemas import TranslationsSchema, build_translations
from utils.language import get_language

if TYPE_CHECKING:
    from django.http import HttpRequest


class ResolverContext(TypedDict):
    request: HttpRequest


class OrganizationSchema(Schema):
    id: str = Field(..., alias="organization_id")
    name: str
    name_translations: TranslationsSchema
    acronym: str
    acronym_translations: TranslationsSchema

    @staticmethod
    def resolve_name(obj: Organization, context: ResolverContext) -> str:
        request = context["request"]
        lang = get_language(request.GET.get("lang"), request.headers)

        return getattr(obj, f"name_{lang}")

    @staticmethod
    def resolve_acronym(obj: Organization, context: ResolverContext) -> str:
        request = context["request"]
        lang = get_language(request.GET.get("lang"), request.headers)

        return getattr(obj, f"acronym_{lang}")

    @staticmethod
    def resolve_name_translations(obj: Organization) -> dict[str, str]:
        return build_translations(obj, "name")

    @staticmethod
    def resolve_acronym_translations(obj: Organization) -> dict[str, str]:
        return build_translations(obj, "acronym")


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
