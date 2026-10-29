from typing import Annotated, Literal, Self
from urllib.parse import urlencode, urlsplit

from iso639 import Lang as IsoLang
from pydantic import (
    AfterValidator,
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
)

from django.conf import settings

from dataservice.models import (
    Dataservice,
    GeoadminFeaturesDataservice,
    OGCAPIStacDataservice,
    WMSDataservice,
    WMTSDataservice,
)
from dataset.models import Dataset, DatasetToUnit
from distribution.models import (
    Distribution,
    ExternalGeoadminFeaturesDistribution,
    ExternalGeoJSONDistribution,
    ExternalWMSDistribution,
    ExternalWMTSDistribution,
)
from organization.models import Organization
from thesaurus.models import ECH0166_THESAURUS_ID, ROOT_CONCEPT_ID
from thesaurus.models import Concept as ConceptModel
from thesaurus.models import Thesaurus as ThesaurusModel


def featureinfo_distribution(dataset: Dataset, dist: Distribution) -> Distribution | None:
    """Return the distribution that serves the feature info of `dataset`, if any.

    Prefer a GeoadminFeatures distribution of the dataset; fall back to the dataset's WMS
    distribution. When resolving for a specific distribution `dist`, a WMS distribution is
    its own feature info source and a WMTS distribution falls back to a WMS sibling; other
    distribution types only get the GeoadminFeatures candidate.
    """
    geoadmin_features = dataset.distribution_set.instance_of(  # ty:ignore[unresolved-attribute]
        ExternalGeoadminFeaturesDistribution
    ).first()
    if geoadmin_features:
        return geoadmin_features
    if isinstance(dist, ExternalWMSDistribution):
        return dist
    if isinstance(dist, ExternalWMTSDistribution):
        return dataset.distribution_set.instance_of(  # ty:ignore[unresolved-attribute]
            ExternalWMSDistribution
        ).first()
    return None


class Lang(BaseModel):
    code: str
    name: str
    dir: str = "ltr"
    alternate: str | None = None


LANGS = {
    "de": Lang(code="de", name="Deutsch", dir="ltr", alternate="German"),
    "fr": Lang(code="fr", name="Français", dir="ltr", alternate="French"),
    "it": Lang(code="it", name="Italiano", dir="ltr", alternate="Italian"),
    "rm": Lang(code="rm", name="Rumantsch", dir="ltr", alternate="Romansh"),
    "en": Lang(code="en", name="English", dir="ltr", alternate="English"),
}


class Link(BaseModel):
    """Base Link object for OAR records.

    The OAR specification defines a Link object with the following properties:
    - href (string): The URL of the linked resource.
    - rel (string, optional): The relationship type of the link.
    - title (string, optional): A human-readable title for the link.
    - type (string, optional): The media type of the linked resource.
    - hreflang (string, optional): The language of the linked resource.

    """

    href: Annotated[str, AfterValidator(lambda v: str(AnyHttpUrl(v)))]
    rel: str | None = None
    title: str | None = None
    typ: str | None = Field(default=None, serialization_alias="type")
    hreflang: str | None = None


def validate_relative_href(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("link must not be empty")

    try:
        parts = urlsplit(value)
    except Exception as e:
        raise ValueError("invalid link") from e
    if parts.scheme:
        raise ValueError("relative link must not have a scheme")
    if parts.netloc:
        raise ValueError("relative link must not have a host")
    return value


class RelativeLink(Link):
    """Relative links require a proper, relative link.

    These links typically point to other records or styles and must be relative as they are
    re-written by service-oa-records.
    """

    href: Annotated[str, AfterValidator(validate_relative_href)]


class UnvalidatedLink(Link):
    """Links that are *not* validated and should be used for all links that are not produced
    by ourselves (partly or wholly) because they rely, for example, on harvested data.
    """

    href: str


class OARCollectionItemsLink(RelativeLink):
    collection_id: str = Field(serialization_alias="collectionId", exclude=True)
    query: dict = Field(default_factory=dict, exclude=True)

    @classmethod
    def from_record_id(cls, collection_id: str, query: dict, **kwargs) -> OARCollectionItemsLink:
        href = f"/collections/{collection_id}/items"
        if query:
            href += f"?{urlencode(query)}"
        return cls(collection_id=collection_id, query=query, href=href, **kwargs)


class OARRecordLink(RelativeLink):
    model_config = ConfigDict(populate_by_name=True)
    collection_id: str = Field(serialization_alias="collectionId", exclude=True)
    record_id: str = Field(serialization_alias="recordId", exclude=True)

    @classmethod
    def from_record_id(cls, collection_id: str, record_id: str, **kwargs) -> OARRecordLink:
        href = f"/collections/{collection_id}/items/{record_id}"
        return cls(collection_id=collection_id, record_id=record_id, href=href, **kwargs)


class OASStyleLink(RelativeLink):
    """Link to a Maplibre style file."""

    distribution_id: str = Field(exclude=True)

    @classmethod
    def from_distribution_id(cls, distribution_id: str, **kwargs) -> OASStyleLink:
        href = f"{settings.OAS_PATH_PREFIX}/{distribution_id}:style"
        return cls(distribution_id=distribution_id, href=href, **kwargs)


class LinkTemplate(BaseModel):
    uri_template: str = Field(serialization_alias="uriTemplate")
    rel: str
    title: str | None = None
    typ: str | None = Field(default=None, serialization_alias="type")
    variables: dict | None = None


class OARRecord(BaseModel):
    id: str
    links: list[Link] = Field(default_factory=list)
    link_templates: list[LinkTemplate] = Field(
        serialization_alias="linkTemplates", default_factory=list
    )
    type: Literal["Feature"] = "Feature"
    geometry: dict | None = None
    lang: str = Field(default="de", exclude=True)
    collection_id: str = Field(default="MISSING", exclude=True)

    def get_key(self) -> str:
        return f"/collections/{self.collection_id}/items/{self.id}.{self.lang}"


class OARDataset(OARRecord):
    """Dataset record

    A Dataset is a Record with type="Dataset"

    """

    properties: dict = Field(default_factory=lambda: {"type": "Dataset"})
    geometry: dict | None = {
        "type": "Polygon",
        # coordinates of the bounding box of Switzerland
        "coordinates": [
            [[5.96, 45.82], [5.96, 47.81], [10.49, 47.81], [10.49, 45.82], [5.96, 45.82]]
        ],
    }

    @classmethod
    def from_dataset(cls, ds: Dataset, lang: str) -> OARDataset:

        contacts = [
            contact
            for legacy_contact in ds.legacy_contacts
            if (contact := Contact.from_legacy(legacy_contact, lang))
        ]

        properties = {
            "contacts": contacts,
            "description": getattr(ds, f"description_{lang}", None),
            "additionalSearchText": ", ".join(getattr(ds, f"additional_search_text_{lang}", [])),
            "language": LANGS[lang],
            "languages": list(LANGS.values()),
            "preferredDistributionId": (  # TODO: needs further clarification
                ds.preferred_distribution.distribution_id if ds.preferred_distribution else None
            ),
            "concepts": [
                concept.concept_id
                for concept in ds.concepts.filter(thesaurus__thesaurus_id=ECH0166_THESAURUS_ID)
            ],
            "title": getattr(ds, f"title_{lang}", None),
            "shortTitle": getattr(ds, f"title_short_{lang}", None),
            "type": "Dataset",
        }
        dataset = OARDataset(
            id=ds.dataset_id,
            properties=properties,
            collection_id=settings.OAR_DATASETS_COLLECTION_ID,
            lang=lang,
        )
        dataset.links.append(
            OARCollectionItemsLink.from_record_id(
                collection_id=settings.OAR_DISTRIBUTIONS_COLLECTION_ID,
                rel="distributions",
                title="Distributions",
                query={"dataset": ds.dataset_id},
            )
        )

        dataset.links.append(
            UnvalidatedLink(
                href=f"https://www.geocat.ch/geonetwork/srv/{IsoLang(lang).pt2b}/catalog.search#/metadata/{ds.geocat_id}",
                rel="alternate",
                title="GeoCat Metadata",
                typ="text/html",
            )
        )

        owner = (
            DatasetToUnit.objects.filter(dataset=ds, role=DatasetToUnit.Role.OWNER)
            .select_related("unit__organization")
            .first()
        )
        if owner:
            organization = owner.unit.organization
            dataset.properties["owner"] = Owner(
                id=organization.organization_id,
                name=getattr(organization, f"name_{lang}", None) or organization.name_de,
                acronym=getattr(organization, f"acronym_{lang}", None) or organization.acronym_de,
            )
        if ds.attribution:
            # Note that the structure of the attribution property is not defined in the OGC API
            # Records specification. There is a stac extension for attribution but at the moment
            # it's too basic since it's just one string attribute `attribution`.
            # There's an issue checking for the possibility to add more structured attribution
            # information: https://github.com/stac-extensions/attribution/issues/1
            dataset.properties["attribution"] = {
                "abbreviation": getattr(ds.attribution, f"abbreviation_{lang}", None),
                "name": getattr(ds.attribution, f"name_{lang}", None),
            }
            url = getattr(ds.attribution, f"url_{lang}", None)
            if url:
                dataset.properties["attribution"]["links"] = [
                    UnvalidatedLink(
                        href=url,
                        rel="about",
                        title="Attribution Information",
                        typ="text/html",
                        hreflang=lang,
                    )
                ]

        if ds.is_aggregate:
            dataset.properties["aggregated"] = True

            legacy_part_info_url = getattr(
                ds, f"legacy_part_info_url_{lang}", ds.legacy_part_info_url_de
            )
            if legacy_part_info_url:
                dataset.links.append(
                    UnvalidatedLink(
                        href=legacy_part_info_url,
                        rel="partinfo",
                        title="Information page about the part datasets",
                        typ="text/html",
                    )
                )

        # TODO: Needs clarification before it can be added
        # Link(
        #    href="https://www.some-external-website.ch",
        #    rel="describedby",
        #    title="Details"
        # )

        return dataset


class OARDistribution(OARRecord):
    """Distribution record

    A Distribution is a Record with type="Distribution"
    """

    properties: dict = Field(default_factory=lambda: {"type": "Distribution"})
    geometry: dict | None = None

    @classmethod
    def from_distribution(  # noqa: C901
        cls, dist: Distribution, lang: str
    ) -> OARDistribution:
        record = OARDistribution(
            id=dist.distribution_id,
            collection_id=f"{dist.dataset.dataset_id}.distributions",
            lang=lang,
        )

        # Set properties
        record.properties["title"] = getattr(dist, f"title_{lang}", dist.title_de)
        if description := getattr(dist, f"description_{lang}"):
            record.properties["description"] = description

        record.links.append(
            OARRecordLink.from_record_id(
                collection_id=settings.OAR_DATASETS_COLLECTION_ID,
                record_id=dist.dataset.dataset_id,
                rel="dataset",
                title="Dataset Record",
            )
        )
        record.properties["protocol"] = dist.protocol
        record.properties["metaInformation"] = dist.meta_information
        record.properties["dataset"] = dist.dataset.dataset_id

        # GeoJSON Distributions behave slightly different as they are not linked to a dataservice
        # but directly to a file
        if isinstance(dist, ExternalGeoJSONDistribution):
            url = getattr(dist, f"geojson_url_{lang}", None)
            if url:
                record.links.append(
                    UnvalidatedLink(
                        href=url,
                        rel="about",
                        title="Link to GeoJSON file",
                        typ="application/geo+json",
                    )
                )
                # Add a link to an associated style if there exists one. Note that this uses
                # an unvalidated link as these links are relative and rewritten by the
                # service-oa-records.
                if dist.style_url:
                    record.links.append(
                        UnvalidatedLink(
                            href=dist.style_url,
                            rel="styledBy",
                            title="Link to style file for the GeoJSON layer",
                            typ="application/json",
                        )
                    )
        elif hasattr(dist, "dataservice") and dist.dataservice:
            # TODO: We should probably only export distributions that actually have an
            # associated dataservice, as otherwise the distribution record would be
            # quite incomplete and not very useful. We'll need to introduce some
            # "publication status" or similar for distributions anyway and add validation
            # when transitioning distributions to "published" status.
            # Note: The linter cannot resolve the dataservice attribute since it's defined
            # in the child classes of the distribution base class
            record.links.append(
                OARRecordLink.from_record_id(
                    collection_id=settings.OAR_SERVICES_COLLECTION_ID,
                    record_id=dist.dataservice.dataservice_id,  # ty:ignore[unresolved-attribute]
                    rel="dataservice",
                )
            )
            record.properties["externalIds"] = [dist.external_record_id(lang)]

        info_dist = featureinfo_distribution(dist.dataset, dist)
        if info_dist:
            record.links.append(
                OARRecordLink.from_record_id(
                    collection_id=settings.OAR_DISTRIBUTIONS_COLLECTION_ID,
                    record_id=info_dist.distribution_id,
                    rel="featureinfo",
                )
            )

        # Add style relation
        if isinstance(dist, (ExternalWMSDistribution, ExternalWMTSDistribution)):
            record.links.append(
                OASStyleLink.from_distribution_id(
                    distribution_id=dist.distribution_id,
                    rel="styledBy",
                    title="Style informations for WM(T)S Layer (Maplibre Style Spec)",
                    typ="application/json",
                )
            )

        if isinstance(dist, ExternalGeoadminFeaturesDistribution):
            if dist.renderable:
                # We use the relation `preview` here, as the HTML popup can be seen as a preview
                # or human-readable representation of the data behind the distribution.
                # htmlpopup_url = getattr(dist, f"htmlpopup_url_{lang}", None)
                htmlpopup_url_base = "https://api3.geo.admin.ch/rest/services/ech/MapServer/"
                record.link_templates.append(
                    LinkTemplate(
                        uri_template=f"{htmlpopup_url_base}{dist.external_record_id(lang)}/{{featureId}}/htmlPopup?lang={{lang}}",
                        rel="preview",
                        typ="application/html",
                        title="HTML popup for a feature of this distribution",
                        variables={
                            "featureId": {
                                "type": "string",
                                "description": "Feature ID",
                            },
                            "lang": {
                                "type": "string",
                                "enum": ["de", "fr", "it", "en"],
                                "default": "de",
                                "description": "Language code",
                            },
                        },
                    )
                )
            if dist.queryable:
                record.properties["queryable"] = True
            if dist.renderable:
                record.properties["renderable"] = True

        return record


class OARDataservice(OARRecord):
    """Service record

    A Service is a Record with type="Service"
    """

    properties: dict = {}

    @classmethod
    def from_dataservice(cls, ds: Dataservice, lang: str) -> OARDataservice:

        # Instantiate record with common properties
        record = OARDataservice(
            id=ds.dataservice_id, lang=lang, collection_id=settings.OAR_SERVICES_COLLECTION_ID
        )

        # Set common properties
        record.properties["title"] = getattr(ds, "title", None)
        record.properties["type"] = "DataService"
        record.properties["protocol"] = ds.service_type

        # Add links
        if ds.documentation_url_de:
            record.links.append(
                UnvalidatedLink(
                    href=ds.documentation_url_de,
                    rel="service-doc",
                    title="Service Documentation (DE)",
                    typ="text/html",
                )
            )
        if ds.openapi_spec_url:
            record.links.append(
                UnvalidatedLink(
                    href=ds.openapi_spec_url,
                    rel="service-desc",
                    typ="application/json",
                    title="OpenAPI Specification",
                )
            )

        # Handle service-specific links
        if isinstance(ds, WMTSDataservice):
            url = ds.localized_capabilities_url(lang)
            if "{epsg}" in url:
                record.link_templates.append(
                    LinkTemplate(
                        uri_template=url,
                        rel="describedby",
                        typ="application/xml",
                        title="WMTS Capabilities File",
                        variables={
                            "epsg": {
                                "enum": ds.variable_epsg_list,
                                "type": "number",
                                "format": "integer",
                                "default": 2056,
                                "description": "EPSG",
                            }
                        },
                    )
                )
            else:
                record.links.append(
                    UnvalidatedLink(
                        href=url,
                        rel="describedby",
                        typ="application/xml",
                        title="WMTS Capabilities File",
                    )
                )

        elif isinstance(ds, WMSDataservice):
            record.links.append(
                UnvalidatedLink(
                    href=ds.localized_capabilities_url(lang),
                    rel="describedby",
                    typ="application/xml",
                    title="WMS Capabilities File",
                )
            )
        elif isinstance(ds, OGCAPIStacDataservice):
            record.links.append(
                UnvalidatedLink(
                    href=ds.landing_page_url,
                    rel="describedby",
                    typ="application/json",
                    title="Landing Page of the OGC API Features/STAC Dataservice",
                )
            )
        elif isinstance(ds, GeoadminFeaturesDataservice):
            record.links.append(
                UnvalidatedLink(
                    href=ds.landing_page_url,
                    rel="describes",
                    typ="application/json",
                    title="Root URL of the Geoadmin Features Dataservice",
                )
            )

        return record


class OAROrganization(OARRecord):
    """Organization record

    An organization is a Record with type="Organization"
    """

    properties: dict = {}

    @classmethod
    def from_organization(cls, organization: Organization, lang: str) -> OAROrganization:

        # Instantiate record with common properties
        record = OAROrganization(
            id=organization.organization_id,
            lang=lang,
            collection_id=settings.OAR_ORGANIZATIONS_COLLECTION_ID,
        )

        # Set common properties
        record.properties["type"] = "Organization"
        record.properties["name"] = getattr(organization, f"name_{lang}", None)
        record.properties["acronym"] = getattr(organization, f"acronym_{lang}", None)

        return record


class ContactEntry(BaseModel):
    """A phone number or email address of a contact.

    Follows the `phones`/`emails` items of the OGC API Records contact schema.
    """

    value: str
    roles: list[str] | None = None


class ContactAddress(BaseModel):
    """A physical address of a contact (an `addresses` item of the OGC contact schema)."""

    delivery_point: list[str] | None = Field(default=None, serialization_alias="deliveryPoint")
    city: str | None = None
    administrative_area: str | None = Field(default=None, serialization_alias="administrativeArea")
    postal_code: str | None = Field(default=None, serialization_alias="postalCode")
    country: str | None = None


class Contact(BaseModel):
    """A contact of a dataset, following the OGC API Records contact schema.

    See https://schemas.opengis.net/ogcapi/records/part1/1.0/openapi/schemas/contact.yaml
    """

    organization: str | None = None
    position: str | None = None
    phones: list[ContactEntry] = Field(default_factory=list)
    emails: list[ContactEntry] = Field(default_factory=list)
    addresses: list[ContactAddress] = Field(default_factory=list)
    links: list[UnvalidatedLink] = Field(default_factory=list)
    roles: list[str] | None = None

    @classmethod
    def from_legacy(cls, legacy_contact: dict, lang: str) -> Self | None:
        """Build a Contact from a `Dataset.legacy_contacts` entry.

        Returns None when the entry has no organization name, as the OGC contact
        schema requires at least one of `name` or `organization` and the legacy
        data never contains a person name.
        """
        organization = legacy_contact.get(f"org_name_{lang}") or legacy_contact.get("org_name")
        if not organization:
            return None

        phones = []
        if voice := legacy_contact.get("contact_voice"):
            phones.append(ContactEntry(value=voice, roles=["work"]))
        if facsimile := legacy_contact.get("contact_facsimile"):
            phones.append(ContactEntry(value=facsimile, roles=["fax"]))
        if sms := legacy_contact.get("contact_sms"):
            phones.append(ContactEntry(value=sms, roles=["sms"]))

        emails = [
            ContactEntry(value=email)
            for email in legacy_contact.get("contact_electronic_mail_addresses") or []
        ]

        address = ContactAddress(
            delivery_point=(
                [legacy_contact["contact_delivery_point"]]
                if legacy_contact.get("contact_delivery_point")
                else None
            ),
            city=legacy_contact.get("contact_city"),
            administrative_area=legacy_contact.get("contact_administrative_area"),
            postal_code=legacy_contact.get("contact_postal_code"),
            country=legacy_contact.get("contact_country"),
        )

        links = []
        for resource in legacy_contact.get("online_resources") or []:
            if url := resource.get(f"url_{lang}"):
                hreflang = lang
                title = resource.get(f"name_{lang}")
            elif url := resource.get("url"):
                hreflang = None
                title = None
            else:
                continue
            links.append(
                UnvalidatedLink(
                    href=url,
                    typ="text/html",
                    hreflang=hreflang,
                    title=title,
                )
            )
        return cls(
            organization=organization,
            position=legacy_contact.get(f"position_name_{lang}"),
            phones=phones,
            emails=emails,
            addresses=[address],
            links=links,
            roles=[legacy_contact["role"]] if legacy_contact.get("role") else None,
        )


class Owner(BaseModel):
    """The organization owning a dataset, localized to the record language."""

    id: str
    name: str
    acronym: str


class PaintConfig(BaseModel):
    """A Maplibre paint definition.

    See https://maplibre.org/maplibre-style-spec/layers/#paint.

    Note that raster-gutter is actually not part of the specs.
    """

    raster_opacity: float | None = Field(
        default=1.0, ge=0.0, le=1.0, serialization_alias="raster-opacity"
    )
    raster_gutter: int | None = Field(
        default=None, ge=0, le=1000, serialization_alias="raster-gutter"
    )

    # We forbid to add extra fields since we want to have control over the fields
    model_config = ConfigDict(extra="forbid")


class MaplibreStyle(BaseModel):
    """A Maplibre style definition

    A Maplibre style definition is basically a JSON object with specific
    root level and nested properties. We currently use only the `layers` root
    property.

    See https://maplibre.org/maplibre-style-spec/layers/.
    """

    layers: list[MaplibreLayer] = []


class MaplibreLayer(BaseModel):
    """A generic Maplibre layer definition.

    See https://maplibre.org/maplibre-style-spec/layers/#layer-properties.
    """

    id: str
    source: str
    typ: str = Field(serialization_alias="type")
    paint: PaintConfig = PaintConfig()


class MaplibreRasterLayer(MaplibreLayer):
    """A Maplibre raster layer definition.

    See https://maplibre.org/maplibre-style-spec/layers/#layer-properties.
    """

    typ: Literal["raster"] = Field(default="raster", serialization_alias="type")  # ty: ignore[invalid-mutable-override]


class OARThesaurus(OARRecord):
    """Thesaurus record

    A thesaurus is a Record with type="Thesaurus".

    The links to the actual thesauri are added as relative links and rewritten to absolute links
    in service-oa-recrds (with the same host).
    """

    properties: dict = {}

    @classmethod
    def from_thesaurus(cls, thesaurus: ThesaurusModel, lang: str) -> OARThesaurus:

        # Instantiate record with common properties
        record = OARThesaurus(
            id=thesaurus.thesaurus_id,
            lang=lang,
            collection_id=settings.OAR_THESAURI_COLLECTION_ID,
        )

        record.properties["type"] = "Thesaurus"
        record.links.extend(
            [
                UnvalidatedLink(
                    rel="about",
                    title="Thesaurus (custom JSON format)",
                    typ="application/json",
                    href=f"{settings.THESAURI_PATH_PREFIX}/{thesaurus.thesaurus_id}.{lang}.json",
                    hreflang=lang,
                ),
                UnvalidatedLink(
                    rel="about",
                    title="Thesaurus (SKOS JSON-LD)",
                    typ="application/ld+json",
                    href=f"{settings.THESAURI_PATH_PREFIX}/{thesaurus.thesaurus_id}.json",
                ),
            ]
        )

        return record


class Concept(BaseModel):
    concept_id: str
    label: str
    children: list[Concept]

    @classmethod
    def from_concept(cls, concept: ConceptModel, lang: str) -> Concept:
        return cls(
            concept_id=concept.concept_id,
            label=getattr(concept, f"label_{lang}"),
            children=[cls.from_concept(child, lang) for child in concept.children.all()],  # ty: ignore[unresolved-attribute]
        )


class Thesaurus(BaseModel):
    thesaurus_id: str
    concepts: list[Concept]

    @classmethod
    def from_thesaurus(cls, thesaurus: ThesaurusModel, lang: str) -> Thesaurus:
        roots = ConceptModel.objects.filter(
            thesaurus=thesaurus,
            parent__concept_id=ROOT_CONCEPT_ID,
        )
        return cls(
            thesaurus_id=thesaurus.thesaurus_id,
            concepts=[Concept.from_concept(c, lang) for c in roots],
        )
