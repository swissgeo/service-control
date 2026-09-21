from enum import StrEnum

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router

from thesaurus.models import ROOT_CONCEPT_ID, Concept, Thesaurus
from thesaurus.schemas import ConceptSchema
from utils.language import LanguageCode

router = Router(tags=["Thesauri"])


class FormatCode(StrEnum):
    JSON = "json"


@router.get(
    path="/thesauri/{thesaurus_id}",
    summary="Get thesaurus",
    response={200: list[ConceptSchema]},
    exclude_none=True,
)
def thesaurus(
    request: HttpRequest,
    thesaurus_id: str,
    format: FormatCode = FormatCode.JSON,  # noqa: A002, ARG001
    lang: LanguageCode = LanguageCode.ENGLISH,
) -> QuerySet[Concept]:
    """
    Get the full thesaurus.
    """
    thesaurus = get_object_or_404(Thesaurus, thesaurus_id=thesaurus_id)
    return Concept.objects.filter(thesaurus=thesaurus, parent__concept_id=ROOT_CONCEPT_ID).order_by(
        f"label_{lang}"
    )
