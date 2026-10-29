from ninja import Field, Schema

from organization.models import Organization, Unit
from schemas import ResolverContext, TranslationsSchema, build_translations
from utils.language import get_language


class OrganizationSchema(Schema):
    id: str = Field(alias="organization_id")
    name: str
    name_translations: TranslationsSchema
    abbreviation: str
    abbreviation_translations: TranslationsSchema

    @staticmethod
    def resolve_name(obj: Organization, context: ResolverContext) -> str:
        """Resolves value of name field by getting the name in the appropriate
        language based on the request context."""
        request = context["request"]
        lang = get_language(request.GET.get("lang"), request.headers)

        return getattr(obj, f"name_{lang}")

    @staticmethod
    def resolve_abbreviation(obj: Organization, context: ResolverContext) -> str:
        """Resolves value of abbreviation field by getting the abbreviation in the appropriate
        language based on the request context."""
        request = context["request"]
        lang = get_language(request.GET.get("lang"), request.headers)

        return getattr(obj, f"abbreviation_{lang}")

    @staticmethod
    def resolve_name_translations(obj: Organization) -> dict[str, str]:
        """Resolves value of name_translations field."""
        return build_translations(obj, "name")

    @staticmethod
    def resolve_abbreviation_translations(obj: Organization) -> dict[str, str]:
        """Resolves value of abbreviation_translations field."""
        return build_translations(obj, "abbreviation")


class OrganizationListSchema(Schema):
    items: list[OrganizationSchema]


class CreateOrganizationSchema(Schema):
    id: str
    name_translations: TranslationsSchema
    abbreviation_translations: TranslationsSchema


class UpdateOrganizationSchema(Schema):
    name_translations: TranslationsSchema
    abbreviation_translations: TranslationsSchema


class UnitSchema(Schema):
    id: str = Field(alias="unit_id")
    name: str
    name_translations: TranslationsSchema
    organization_id: str = Field(alias="organization.organization_id")

    @staticmethod
    def resolve_name(obj: Unit, context: ResolverContext) -> str:
        """Resolves value of name field by getting the name in the appropriate
        language based on the request context."""
        request = context["request"]
        lang = get_language(request.GET.get("lang"), request.headers)

        return getattr(obj, f"name_{lang}")

    @staticmethod
    def resolve_name_translations(obj: Unit) -> dict[str, str]:
        """Resolves value of name_translations field."""
        return build_translations(obj, "name")


class UnitListSchema(Schema):
    items: list[UnitSchema]


class CreateUnitSchema(Schema):
    id: str
    name_translations: TranslationsSchema
    organization_id: str


class UpdateUnitSchema(Schema):
    name_translations: TranslationsSchema
