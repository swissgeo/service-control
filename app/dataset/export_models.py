from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from dataservice.models import (
    Dataservice,
    OGCAPIStacDataservice,
    WMSDataservice,
    WMTSDataservice,
)
from distribution.models import Distribution, ExternalGeoJSONDistribution

if TYPE_CHECKING:
    from dataset.models import Dataset


class Lang(BaseModel):
    code: str
    name: str
    dir: str = "ltr"
    alternate: str | None = None


LANGS = {
    "de": Lang(code="de", name="Deutsch", dir="ltr", alternate="German"),
    "fr": Lang(code="fr", name="Français", dir="ltr", alternate="French"),
    "it": Lang(code="it", name="Italiano", dir="ltr", alternate="Italian"),
    "en": Lang(code="en", name="English", dir="ltr"),
}


def is_url(url: str) -> str:
    if not url.startswith("http"):
        raise ValueError(f"{url} is not a valid URL")
    return url


class BaseLink(BaseModel):
    """Base Link object for OAR records

    The OAR specification defines a Link object with the following properties:
    - href (string): The URL of the linked resource. This is optional in the base class.
    - rel (string, required): The relationship type of the link.
    - title (string, optional): A human-readable title for the link.
    - type (string, optional): The media type of the linked resource.
    - hreflang (string, optional): The language of the linked resource.

    """

    href: Annotated[str, AfterValidator(is_url)] | None = None
    rel: str
    title: str | None = None
    typ: str | None = Field(default="application/json", serialization_alias="type")
    hreflang: str | None = None


class Link(BaseLink):
    """Generic Link object for OAR records

    Unlike in the base class, the href property is required in this class, as it represents a fully
    defined link to an external resource. This class can be used for links that point to
    resources outside of the OAR service.:
    - href (string, required): The URL of the linked resource.
    """

    href: Annotated[str, AfterValidator(is_url)]


class OARLink(BaseLink):
    """Link object for endpoints within the OAR service

    This is a base class for links that point to endpoints within the OAR service itself.
    - fqdn (string): The fully qualified domain name of the OAR service
      (e.g. "services.dev.sgdi.tech")
    - basepath (string): The base path of the OAR API (e.g. "/api/oar/v0")

    """

    # These are "private" fields that should not be included in a model_dump
    fqdn: str = Field(exclude=True, default="services.dev.sgdi.tech")
    basepath: str = Field(exclude=True, default="/api/oar/v0")


class OARCollectionLink(OARLink):
    collectionId: str = Field(exclude=True)  # noqa: N815

    @model_validator(mode="after")
    def generate_href_value(self) -> OARLink:
        """Generate the href value for the record link.

        This method is called after the model is initialized and will set the href value
        based on the fqdn, basepath, collectionId and recordId.
        """
        self.href = f"https://{self.fqdn}{self.basepath}/collections/{self.collectionId}"
        if self.hreflang:
            self.href += f"?language={self.hreflang}"
        return self


class OARRecordLink(OARCollectionLink):
    model_config = ConfigDict(populate_by_name=True)
    recordId: str = Field(exclude=True)  # noqa: N815

    @model_validator(mode="after")
    def generate_href_value(self) -> OARLink:
        """Generate the href value for the record link.

        This method is called after the model is initialized and will set the href value
        based on the fqdn, basepath, collectionId and recordId.
        """
        self.href = f"https://{self.fqdn}{self.basepath}/collections/{self.collectionId}/items/{self.recordId}"
        if self.hreflang:
            self.href += f"?language={self.hreflang}"
        return self


class LinkTemplate(BaseModel):
    uriTemplate: str  # noqa: N815
    rel: str
    title: str | None = None
    typ: str | None = Field(default=None, serialization_alias="type")
    variables: dict | None = None


class OARRecord(BaseModel):
    id: str
    links: list[BaseLink] = Field(default_factory=list)
    linkTemplates: list[LinkTemplate] = Field(default_factory=list)  # noqa: N815
    type: Literal["Feature"] = "Feature"
    geometry: dict | None = None


class OARDataset(OARRecord):
    """Dataset record

    A Dataset is a Record with type="Dataset"

    """

    properties: dict = Field(default_factory=lambda: {"type": "Dataset"})
    geometry: dict | None = {
        "type": "Polygon",
        "coordinates": [
            [[5.96, 45.82], [5.96, 47.81], [10.49, 47.81], [10.49, 45.82], [5.96, 45.82]]
        ],
    }

    @classmethod
    def from_dataset(cls, ds: Dataset, lang: str) -> OARDataset:
        record = OARDataset(id=ds.dataset_id)

        # Set properties
        record.properties["title"] = getattr(ds, f"title_short_{lang}", None)
        record.properties["description"] = getattr(ds, f"description_{lang}", None)
        # record.properties["preferredDistributionId"] = self.preferred_distribution_id
        record.properties["language"] = LANGS[lang]
        record.properties["languages"] = list(LANGS.values())
        # record.properties["contacts"] = getattr(self, f"contacts_{lang}", [])

        # Add links
        # links = getattr(self, f"links_{lang}", [])
        # for link in links:
        #     record.links.append(link)

        return record


class OARDistribution(OARRecord):
    """Distribution record

    A Distribution is a Record with type="Distribution"
    """

    properties: dict = Field(default_factory=lambda: {"type": "Distribution"})
    geometry: dict | None = None

    @classmethod
    def from_distribution(cls, dist: Distribution, lang: str) -> OARDistribution:
        record = OARDistribution(id=dist.distribution_id)

        # Set properties
        record.properties["title"] = dist.title
        record.links.append(
            OARRecordLink(
                collectionId=dist.dataset.dataset_id,
                recordId=dist.distribution_id,
                rel="self",
                title="Link to this distribution record",
                hreflang=lang,
            )
        )
        record.links.append(
            OARRecordLink(
                collectionId="swissgeo.catalog",
                recordId=dist.dataset.dataset_id,
                rel="dataset",
                hreflang=lang,
                title=f"Link to parent dataset {dist.dataset.dataset_id}",
            )
        )
        record.properties["protocol"] = dist.protocol

        # GeoJSON Distributions behave slightly different as they are not linked to a dataservice
        # but directly to a file
        if isinstance(dist, ExternalGeoJSONDistribution):
            url = getattr(dist, f"geojson_url_{lang}", None)
            if url:
                record.links.append(
                    Link(
                        href=url,
                        rel="about",
                        title="Link to GeoJSON file",
                        typ="application/geo+json",
                    )
                )
                record.links.append(
                    Link(
                        href=dist.style_url,
                        rel="styled-by",
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
                OARRecordLink(
                    collectionId="geoadmin.services",
                    recordId=dist.dataservice.dataservice_id,  # ty:ignore[unresolved-attribute]
                    rel="dataservice",
                )
            )
            record.properties["externalIds"] = [dist.external_id]

        return record


class OARDataservice(OARRecord):
    """Service record

    A Service is a Record with type="Service"
    """

    properties: dict = {}

    @classmethod
    def from_dataservice(cls, ds: Dataservice, lang: str = "de") -> OARDataservice:  # noqa: ARG003

        # Instantiate record with common properties
        record = OARDataservice(id=ds.dataservice_id)

        # Set common properties
        record.properties["title"] = getattr(ds, "title", None)
        record.properties["type"] = ds.service_type

        # Add links
        if ds.documentation_url_de:
            record.links.append(
                Link(
                    href=ds.documentation_url_de,
                    rel="service-doc",
                    title="Service Documentation (DE)",
                )
            )
        if ds.openapi_spec_url:
            record.links.append(
                Link(
                    href=ds.openapi_spec_url,
                    rel="service-desc",
                    typ="application/json",
                    title="OpenAPI Specification",
                )
            )

        # Handle service-specific links
        if isinstance(ds, WMTSDataservice):
            if "{epsg}" in ds.capabilities_url:
                record.linkTemplates.append(
                    LinkTemplate(
                        uriTemplate=ds.capabilities_url,
                        rel="about",
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
                    Link(
                        href=ds.capabilities_url,
                        rel="about",
                        typ="application/xml",
                        title="WMTS Capabilities File",
                    )
                )

        elif isinstance(ds, WMSDataservice):
            if "{lang}" in ds.capabilities_url:
                record.linkTemplates.append(
                    LinkTemplate(
                        uriTemplate=ds.capabilities_url,
                        rel="about",
                        typ="application/xml",
                        title="WMS Capabilities File",
                        variables={
                            "lang": {
                                "enum": ds.languages,
                                "type": "string",
                                "default": "de",
                                "description": "Language code",
                            }
                        },
                    )
                )
            else:
                record.links.append(
                    Link(
                        href=ds.capabilities_url,
                        rel="about",
                        typ="application/xml",
                        title="WMS Capabilities File",
                    )
                )
        elif isinstance(ds, OGCAPIStacDataservice):
            record.links.append(
                Link(
                    href=ds.landing_page_url,
                    rel="describes",
                    typ="application/json",
                    title="Landing Page of the OGC API Features/STAC Dataservice",
                )
            )

        return record


class OARCollection(BaseModel):
    """Record Collection

    The record collection entity has a slightly different structure
    than a record itself.
    Spec: https://developer.ogc.org/api/records/index.html#tag/Collection/operation/describeCollection

    Note the following:
    /collections/{collectionId} will return a Collection with roughly the following structure:
    {
      "id": "string",
      "title": "string",
      "type": "Collection",
      "itemType": "record",
      "recordsArrayName": "records",
      "records": [
        { ... Record ... }
      ]
    }

    /collections/{collectionId}/items will return a FeatureCollection with roughly
    the following structure:
    {
      "type": "FeatureCollection",
      "features": [
        { ... Record ... }
      ]
    }

    Unfortunately, the record array attribute names differ between the two endpoints.
    For now we'll implement only the /collections/{collectionId} structure and use the
    inline 'records' array. The /items endpoint will be implemented later once we have
    service-control in place to serve those endpoints. We'll then remove the inline
    'records' array from the Collection and instead add a link with rel="items" to
    point to the /items endpoint.

    """

    id: str
    title: str
    type: str = "Collection"
    itemType: str = "record"  # noqa: N815
    recordsArrayName: str = "records"  # noqa: N815
    records: list[Any] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)


class OAFeatureCollection(BaseModel):
    typ: str = Field(default="FeatureCollection", serialization_alias="type")
    features: list[OARDistribution | OARDataset | OARDataservice] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)


class Contact(BaseModel):
    organization: str
    country: str
    role: str
    # name: Optional[str] = None
    # position: Optional[str] = None
    # email: Optional[str] = None
    # phone: Optional[str] = None
    # address: Optional[str] = None
    # city: Optional[str] = None
    # postal_code: Optional[str] = None
