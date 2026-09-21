from ninja import Schema

from schemas import ResolverContext, TranslationsSchema, build_translations
from thesaurus.models import Concept
from utils.language import get_language


class ConceptSchema(Schema):
    concept_id: str
    label: str
    label_translations: TranslationsSchema
    children: list[ConceptSchema]

    @staticmethod
    def resolve_label(obj: Concept, context: ResolverContext) -> str:
        request = context["request"]
        lang = get_language(request.GET.get("lang"), request.headers)
        return getattr(obj, f"label_{lang}")

    @staticmethod
    def resolve_label_translations(obj: Concept) -> dict[str, str]:
        return build_translations(obj, "label")

    @staticmethod
    def resolve_children(obj: Concept, context: ResolverContext) -> list[Concept]:
        request = context["request"]
        lang = get_language(request.GET.get("lang"), request.headers)
        children = obj.children  # ty: ignore[unresolved-attribute]
        if isinstance(children, list):
            # ninja seems to sometimes return a DjangoGetter, which already resolve the children
            return sorted(children, key=lambda child: getattr(child, f"label_{lang}"))
        return children.order_by(f"label_{lang}")
