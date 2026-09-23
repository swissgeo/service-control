from django.db.models import QuerySet
from ninja import Schema

from schemas import ResolverContext, TranslationsSchema, build_translations
from thesaurus.models import ROOT_CONCEPT_ID, Concept, Thesaurus
from utils.language import get_language


class ThesaurusSchema(Schema):
    thesaurus_id: str
    concepts: list[ConceptSchema]

    @staticmethod
    def resolve_concepts(obj: Thesaurus) -> QuerySet[Concept]:
        return Concept.objects.filter(thesaurus=obj, parent__concept_id=ROOT_CONCEPT_ID)


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
