from ninja import Field, Schema

from organization.models import Organization, Unit  # noqa: TC001
from schemas import ResolverContext, TranslationsSchema, build_translations
from utils.language import get_language


class OrganizationSchema(Schema):
    id: str = Field(alias="organization_id")
    name: str
    name_translations: TranslationsSchema
    acronym: str
    acronym_translations: TranslationsSchema

    @staticmethod
    def resolve_name(obj: Organization, context: ResolverContext) -> str:
        """Resolves value of name field by getting the name in the appropriate
        language based on the request context."""
        request = context["request"]
        lang = get_language(request.GET.get("lang"), request.headers)

        return getattr(obj, f"name_{lang}")

    @staticmethod
    def resolve_acronym(obj: Organization, context: ResolverContext) -> str:
        """Resolves value of acronym field by getting the acronym in the appropriate
        language based on the request context."""
        request = context["request"]
        lang = get_language(request.GET.get("lang"), request.headers)

        return getattr(obj, f"acronym_{lang}")

    @staticmethod
    def resolve_name_translations(obj: Organization) -> dict[str, str]:
        """Resolves value of name_translations field."""
        return build_translations(obj, "name")

    @staticmethod
    def resolve_acronym_translations(obj: Organization) -> dict[str, str]:
        """Resolves value of acronym_translations field."""
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
