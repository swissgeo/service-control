from enum import StrEnum

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router

from thesaurus.models import Thesaurus
from thesaurus.schemas import ThesaurusSchema
from thesaurus.utils import thesaurus_to_skos_jsonld
from utils.language import LanguageCode

router = Router(tags=["Thesauri"])


class FormatCode(StrEnum):
    JSON = "json"
    JSON_LD = "jsonld"


@router.get(
    path="/thesauri/{thesaurus_id}",
    summary="Get thesaurus",
    response={200: ThesaurusSchema},
    exclude_none=True,
)
def thesaurus(
    request: HttpRequest,
    thesaurus_id: str,
    format: FormatCode = FormatCode.JSON,  # noqa: A002
    lang: LanguageCode = LanguageCode.ENGLISH,
) -> Thesaurus | HttpResponse:
    """
    Get the full thesaurus.
    """
    thesaurus = get_object_or_404(Thesaurus, thesaurus_id=thesaurus_id)

    if format is FormatCode.JSON_LD:
        return HttpResponse(thesaurus_to_skos_jsonld(thesaurus), content_type="application/ld+json")

    return thesaurus
