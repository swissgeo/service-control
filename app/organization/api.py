from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router

from utils.language import LanguageCode, get_language, get_translation

from .models import Organization, OrganizationUnit
from .schemas import (
    CreateOrganizationSchema,
    CreateOrganizationUnitSchema,
    OrganizationListSchema,
    OrganizationSchema,
    OrganizationUnitListSchema,
    OrganizationUnitSchema,
    TranslationsSchema,
    UpdateOrganizationSchema,
    UpdateOrganizationUnitSchema,
)

router = Router()


def organization_to_response(model: Organization, lang: LanguageCode) -> OrganizationSchema:
    """
    Transforms the given model using the given language into a response object.
    """
    return OrganizationSchema(
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
        ),
    )


@router.post("/organizations", response={201: OrganizationSchema}, exclude_none=True)
def create_organization(
    request: HttpRequest,
    organization_in: CreateOrganizationSchema,
    lang: LanguageCode | None = None,
) -> OrganizationSchema:
    """Create an organization.

    TODO: Authorization should only be available to swissgeo-admin users.
    """
    lang_to_use = get_language(lang, request.headers)
    org = Organization.objects.create(
        organization_id=organization_in.id,
        name_de=organization_in.name_translations.de,
        name_fr=organization_in.name_translations.fr,
        name_en=organization_in.name_translations.en,
        name_it=organization_in.name_translations.it,
        name_rm=organization_in.name_translations.rm,
        acronym_de=organization_in.acronym_translations.de,
        acronym_fr=organization_in.acronym_translations.fr,
        acronym_en=organization_in.acronym_translations.en,
        acronym_it=organization_in.acronym_translations.it,
        acronym_rm=organization_in.acronym_translations.rm,
    )
    return organization_to_response(org, lang_to_use)


@router.put(
    "/organizations/{organization_id}",
    response={200: OrganizationSchema},
    exclude_none=True,
)
def update_organization(
    request: HttpRequest,
    organization_id: str,
    organization_in: UpdateOrganizationSchema,
    lang: LanguageCode | None = None,
) -> OrganizationSchema:
    """Update an organization.

    TODO: Authorization should only be available to swissgeo-admin users.
    """
    lang_to_use = get_language(lang, request.headers)

    org = get_object_or_404(Organization, organization_id=organization_id)
    org.name_de = organization_in.name_translations.de
    org.name_fr = organization_in.name_translations.fr
    org.name_en = organization_in.name_translations.en
    org.name_it = organization_in.name_translations.it
    org.name_rm = organization_in.name_translations.rm
    org.acronym_de = organization_in.acronym_translations.de
    org.acronym_fr = organization_in.acronym_translations.fr
    org.acronym_en = organization_in.acronym_translations.en
    org.acronym_it = organization_in.acronym_translations.it
    org.acronym_rm = organization_in.acronym_translations.rm
    org.save()

    return organization_to_response(org, lang_to_use)


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
    lang: LanguageCode | None = None,
) -> OrganizationSchema:
    """
    Get details of an organization.

    TODO: Authorization, should only be available to organization admin.
    """
    model = get_object_or_404(Organization, organization_id=organization_id)
    lang_to_use = get_language(lang, request.headers)
    return organization_to_response(model, lang_to_use)


def organization_unit_to_response(
    model: OrganizationUnit, lang: LanguageCode
) -> OrganizationUnitSchema:
    """
    Transforms the given model using the given language into a response object.
    """
    return OrganizationUnitSchema(
        id=model.organization_unit_id,
        organization_id=model.organization.organization_id,
        name=get_translation(model, "name", lang),
        name_translations=TranslationsSchema(
            de=model.name_de,
            fr=model.name_fr,
            en=model.name_en,
            it=model.name_it,
            rm=model.name_rm,
        ),
    )


@router.post(
    "/organizations/{organization_id}/orgunits",
    response={201: OrganizationUnitSchema},
    exclude_none=True,
)
def create_organization_unit(
    request: HttpRequest,
    organization_id: str,
    organization_unit_in: CreateOrganizationUnitSchema,
    lang: LanguageCode | None = None,
) -> OrganizationUnitSchema:
    """Create an organization unit.
    TODO: Authorization should only be available to organization admin.
    """
    lang_to_use = get_language(lang, request.headers)
    org = get_object_or_404(Organization, organization_id=organization_id)
    org_unit = OrganizationUnit.objects.create(
        organization=org,
        organization_unit_id=organization_unit_in.id,
        name_de=organization_unit_in.name_translations.de,
        name_fr=organization_unit_in.name_translations.fr,
        name_en=organization_unit_in.name_translations.en,
        name_it=organization_unit_in.name_translations.it,
        name_rm=organization_unit_in.name_translations.rm,
    )
    return organization_unit_to_response(org_unit, lang_to_use)


@router.put(
    "/organizations/{organization_id}/orgunits/{organization_unit_id}",
    response={200: OrganizationUnitSchema},
    exclude_none=True,
)
def update_organization_unit(
    request: HttpRequest,
    organization_id: str,
    organization_unit_id: str,
    organization_unit_in: UpdateOrganizationUnitSchema,
    lang: LanguageCode | None = None,
) -> OrganizationUnitSchema:
    """Update an organization unit.

    TODO: Authorization should only be available to organization admin.
    """
    lang_to_use = get_language(lang, request.headers)

    org_unit = get_object_or_404(
        OrganizationUnit,
        organization__organization_id=organization_id,
        organization_unit_id=organization_unit_id,
    )
    org_unit.name_de = organization_unit_in.name_translations.de
    org_unit.name_fr = organization_unit_in.name_translations.fr
    org_unit.name_en = organization_unit_in.name_translations.en
    org_unit.name_it = organization_unit_in.name_translations.it
    org_unit.name_rm = organization_unit_in.name_translations.rm
    org_unit.save()

    return organization_unit_to_response(org_unit, lang_to_use)


@router.get(
    "/organizations/{organization_id}/orgunits",
    response={200: OrganizationUnitListSchema},
    exclude_none=True,
)
def organization_units(
    request: HttpRequest, organization_id: str, lang: LanguageCode | None = None
) -> OrganizationUnitListSchema:
    """
    List all organization units for a given organization.

    TODO: Authorization should only be available to organization admin ??
    """
    models = OrganizationUnit.objects.filter(
        organization__organization_id=organization_id
    ).order_by("id")
    lang_to_use = get_language(lang, request.headers)
    response = [organization_unit_to_response(model, lang_to_use) for model in models]
    return OrganizationUnitListSchema(items=response)


@router.get(
    "/organizations/{organization_id}/orgunits/{organization_unit_id}",
    response={200: OrganizationUnitSchema},
    exclude_none=True,
)
def organization_unit(
    request: HttpRequest,
    organization_id: str,
    organization_unit_id: str,
    lang: LanguageCode | None = None,
) -> OrganizationUnitSchema:
    """
    Get details of an organization unit.

    TODO: Authorization should only be available to organization admin.
    """
    model = get_object_or_404(
        OrganizationUnit,
        organization__organization_id=organization_id,
        organization_unit_id=organization_unit_id,
    )
    lang_to_use = get_language(lang, request.headers)
    return organization_unit_to_response(model, lang_to_use)


@router.delete(
    "/organizations/{organization_id}/orgunits/{organization_unit_id}",
    response={204: None},
)
def delete_organization_unit(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,
    organization_unit_id: str,
) -> None:
    """Delete an organization unit.

    TODO: Authorization should only be available to organization admin.
    """
    org_unit = get_object_or_404(
        OrganizationUnit,
        organization__organization_id=organization_id,
        organization_unit_id=organization_unit_id,
    )
    org_unit.delete()
