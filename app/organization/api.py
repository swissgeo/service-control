from ninja import Router
from utils.language import LanguageCode
from utils.language import get_language
from utils.language import get_translation

from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from .models import Organization
from .schemas import OrganizationListSchema
from .schemas import OrganizationSchema
from .schemas import TranslationsSchema

router = Router()


def organization_to_response(model: Organization, lang: LanguageCode) -> OrganizationSchema:
    """
    Transforms the given model using the given language into a response object.
    """
    response = OrganizationSchema(
        id=model.organization_id,
        name=get_translation(model, "name", lang),
        name_translations=TranslationsSchema(
            de=model.name_de,
            fr=model.name_fr,
            en=model.name_en,
            it=model.name_it,
            rm=model.name_rm,
        ),
        acronym=get_translation(model, "acronym", lang),
        acronym_translations=TranslationsSchema(
            de=model.acronym_de,
            fr=model.acronym_fr,
            en=model.acronym_en,
            it=model.acronym_it,
            rm=model.acronym_rm,
        )
    )
    return response


@router.get(
    "/organizations",
    response={200: OrganizationListSchema},
    exclude_none=True,
)
def organizations(request: HttpRequest, lang: LanguageCode | None = None) -> OrganizationListSchema:
    """
    List all organizations.

    TODO: Authorization should only be available to swissgeo-admin users.
    """
    models = Organization.objects.order_by("id").all()
    lang_to_use = get_language(lang, request.headers)
    response = [organization_to_response(model, lang_to_use) for model in models]
    return OrganizationListSchema(items=response)


@router.get(
    "/organizations/{organization_id}",
    response={200: OrganizationSchema},
    exclude_none=True,
)
def organization(
    request: HttpRequest,
    organization_id: str,
    lang: LanguageCode | None = None
) -> OrganizationSchema:
    """
    Get details of an organization.

    TODO: Authorization, should only be available to organization admin.
    """
    model = get_object_or_404(Organization, organization_id=organization_id)
    lang_to_use = get_language(lang, request.headers)
    response = organization_to_response(model, lang_to_use)
    return response
