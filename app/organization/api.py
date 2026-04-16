from typing import Any

from django.http import HttpRequest  # noqa:TC002
from django.shortcuts import get_object_or_404
from ninja import Router

from config.authorization import VPAction
from utils import api_path
from utils.auth import is_authenticated, superuser_auth, vp_auth
from utils.language import LanguageCode, get_language, get_translation

from .models import Organization, Unit
from .schemas import (
    CreateOrganizationSchema,
    CreateUnitSchema,
    OrganizationListSchema,
    OrganizationSchema,
    TranslationsSchema,
    UnitListSchema,
    UnitSchema,
    UpdateOrganizationSchema,
    UpdateUnitSchema,
)

router = Router(tags=["Organizations"])


@router.post(
    "/organizations",
    summary="Create organization",
    response={201: OrganizationSchema},
    exclude_none=True,
    auth=superuser_auth,
)
def create_organization(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_in: CreateOrganizationSchema,
    lang: LanguageCode | None = None,  # noqa: ARG001  to show in api docs
) -> Organization:
    """
    Create an organization.
    """
    return Organization.objects.create(
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


@router.put(
    f"/organizations/{{{api_path.Organization.parameter_name}}}",
    summary="Update organization",
    response={200: OrganizationSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.UPDATE_ORGANIZATION),
)
def update_organization(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,
    organization_in: UpdateOrganizationSchema,
    lang: LanguageCode | None = None,  # noqa: ARG001  to show in api docs
) -> Organization:
    """
    Update an organization.
    """

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

    return org


@router.get(
    "/organizations",
    summary="List organizations",
    response={200: OrganizationListSchema},
    exclude_none=True,
    auth=is_authenticated,
)
def organizations(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    lang: LanguageCode | None = None,  # noqa: ARG001  to show in api docs
) -> dict[str, Any]:
    """
    List all organizations.
    """
    models = Organization.objects.order_by("id").all()
    return {"items": models}


@router.get(
    f"/organizations/{{{api_path.Organization.parameter_name}}}",
    summary="Get organization",
    response={200: OrganizationSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.GET_ORGANIZATION),
)
def organization(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,
    lang: LanguageCode | None = None,  # noqa: ARG001  to show in api docs
) -> Organization:
    """
    Get details of an organization.
    """
    return get_object_or_404(Organization, organization_id=organization_id)


def unit_to_response(model: Unit, lang: LanguageCode) -> UnitSchema:
    """
    Transforms the given model using the given language into a response object.
    """
    return UnitSchema(
        id=model.unit_id,
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
    f"/organizations/{{{api_path.Organization.parameter_name}}}/units",
    summary="Create unit",
    response={201: UnitSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.CREATE_UNIT),
)
def create_unit(
    request: HttpRequest,
    organization_id: str,
    unit_in: CreateUnitSchema,
    lang: LanguageCode | None = None,
) -> UnitSchema:
    """
    Create an organization unit.
    """
    lang_to_use = get_language(lang, request.headers)
    org = get_object_or_404(Organization, organization_id=organization_id)
    unit = Unit.objects.create(
        organization=org,
        unit_id=unit_in.id,
        name_de=unit_in.name_translations.de,
        name_fr=unit_in.name_translations.fr,
        name_en=unit_in.name_translations.en,
        name_it=unit_in.name_translations.it,
        name_rm=unit_in.name_translations.rm,
    )
    return unit_to_response(unit, lang_to_use)


@router.put(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/units/{{{api_path.Unit.parameter_name}}}",
    summary="Update unit",
    response={200: UnitSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.UPDATE_UNIT, resource=api_path.Unit),
)
def update_unit(
    request: HttpRequest,
    organization_id: str,
    unit_id: str,
    unit_in: UpdateUnitSchema,
    lang: LanguageCode | None = None,
) -> UnitSchema:
    """
    Update an organization unit.
    """
    lang_to_use = get_language(lang, request.headers)

    unit = get_object_or_404(
        Unit,
        organization__organization_id=organization_id,
        unit_id=unit_id,
    )
    unit.name_de = unit_in.name_translations.de
    unit.name_fr = unit_in.name_translations.fr
    unit.name_en = unit_in.name_translations.en
    unit.name_it = unit_in.name_translations.it
    unit.name_rm = unit_in.name_translations.rm
    unit.save()

    return unit_to_response(unit, lang_to_use)


@router.get(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/units",
    summary="List units",
    response={200: UnitListSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.LIST_UNITS),
)
def units(
    request: HttpRequest, organization_id: str, lang: LanguageCode | None = None
) -> UnitListSchema:
    """
    List all organization units for a given organization.
    """
    models = Unit.objects.filter(organization__organization_id=organization_id).order_by("id")
    lang_to_use = get_language(lang, request.headers)
    response = [unit_to_response(model, lang_to_use) for model in models]
    return UnitListSchema(items=response)


@router.get(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/units/{{{api_path.Unit.parameter_name}}}",
    summary="Get unit",
    response={200: UnitSchema},
    exclude_none=True,
    auth=vp_auth(VPAction.GET_UNIT, resource=api_path.Unit),
)
def unit(
    request: HttpRequest,
    organization_id: str,
    unit_id: str,
    lang: LanguageCode | None = None,
) -> UnitSchema:
    """
    Get details of an organization unit.
    """
    model = get_object_or_404(
        Unit,
        organization__organization_id=organization_id,
        unit_id=unit_id,
    )
    lang_to_use = get_language(lang, request.headers)
    return unit_to_response(model, lang_to_use)


@router.delete(
    f"/organizations/{{{api_path.Organization.parameter_name}}}/units/{{{api_path.Unit.parameter_name}}}",
    summary="Delete unit",
    response={204: None},
    auth=vp_auth(VPAction.DELETE_UNIT, resource=api_path.Unit),
)
def delete_unit(
    request: HttpRequest,  # noqa: ARG001  request is not used but required by ninja
    organization_id: str,
    unit_id: str,
) -> None:
    """
    Delete an organization unit.
    """
    unit = get_object_or_404(
        Unit,
        organization__organization_id=organization_id,
        unit_id=unit_id,
    )
    unit.delete()
