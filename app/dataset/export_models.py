from typing import Annotated, Literal
from urllib.parse import urlencode

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from django.conf import settings

from dataservice.models import (
    Dataservice,
    GeoadminFeaturesDataservice,
    OGCAPIStacDataservice,
    WMSDataservice,
    WMTSDataservice,
)
from dataset.models import Dataset
from distribution.models import (
    Distribution,
    ExternalGeoadminFeaturesDistribution,
    ExternalGeoJSONDistribution,
    ExternalWMSDistribution,
    ExternalWMTSDistribution,
)


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

LANGS_ISO_639_2_B = {
    "de": "ger",
    "fr": "fra",
    "it": "ita",
    "rm": "roh",
    "en": "eng",
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


class OARCollectionLink(BaseLink):
    collectionId: str = Field(exclude=True)  # noqa: N815

    @model_validator(mode="after")
    def generate_href_value(self) -> BaseLink:
        """Generate the href value for the record link.

        This method is called after the model is initialized and will set the href value
        based on the origin, basepath, collectionId and recordId.
        """
        self.href = f"/collections/{self.collectionId}"
        return self


class OARCollectionItemsLink(BaseLink):
    collectionId: str = Field(exclude=True)  # noqa: N815
    query: dict = Field(default_factory=dict, exclude=True)

    @model_validator(mode="after")
    def generate_href_value(self) -> BaseLink:
        """Generate the href value for the record link.

        This method is called after the model is initialized and will set the href value
        based on the origin, basepath, collectionId and recordId.
        """
        self.href = f"/collections/{self.collectionId}/items"

        if self.query:
            self.href += f"?{urlencode(self.query)}"

        return self


class OARRecordLink(OARCollectionLink):
    model_config = ConfigDict(populate_by_name=True)
    recordId: str = Field(exclude=True)  # noqa: N815

    @model_validator(mode="after")
    def generate_href_value(self) -> BaseLink:
        """Generate the href value for the record link.

        This method is called after the model is initialized and will set the href value
        based on the origin, basepath, collectionId and recordId.
        """
        self.href = f"/collections/{self.collectionId}/items/{self.recordId}"
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
            Contact(
                organization=contact.get(f"org_name_{lang}") or contact.get("org_name"),
                country=contact.get("contact_country") or "CH",
                role=contact.get("role"),
            )
            for contact in ds.legacy_contacts
        ]

        properties = {
            "contacts": contacts,
            "description": getattr(ds, f"description_{lang}", None),
            "additionalSearchText": ", ".join(getattr(ds, f"additional_search_text_{lang}", [])),
            "language": LANGS[lang],
            "languages": list(LANGS.values()),
            "preferredDistributionId": ds.preferred_distribution.distribution_id
            if ds.preferred_distribution
            else None,  # TODO: needs further clarification
            "title": getattr(ds, f"title_short_{lang}", None),
            "type": "Dataset",
        }
        dataset = OARDataset(
            id=ds.dataset_id,
            properties=properties,
            collection_id=settings.OAR_DATASETS_COLLECTION_ID,
            lang=lang,
        )
        dataset.links.append(
            OARCollectionItemsLink(
                collectionId=settings.OAR_DISTRIBUTIONS_COLLECTION_ID,
                rel="distributions",
                title="Distributions",
                typ=None,
                query={"dataset": ds.dataset_id},
            )
        )

        dataset.links.append(
            Link(
                href=f"https://www.geocat.ch/geonetwork/srv/{LANGS_ISO_639_2_B[lang]}/catalog.search#/metadata/{ds.geocat_id}",
                rel="alternate",
                title="GeoCat Metadata",
                typ="text/html",
            )
        )

        if ds.is_aggregate:
            dataset.properties["aggregated"] = True

            legacy_part_info_url = getattr(
                ds, f"legacy_part_info_url_{lang}", ds.legacy_part_info_url_de
            )
            if legacy_part_info_url:
                dataset.links.append(
                    Link(
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
            OARRecordLink(
                collectionId=settings.OAR_DATASETS_COLLECTION_ID,
                recordId=dist.dataset.dataset_id,
                rel="dataset",
                title="Dataset Record",
                typ=None,
            )
        )
        record.properties["protocol"] = dist.protocol
        record.properties["metaInformation"] = dist.meta_information

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
                OARRecordLink(
                    collectionId=settings.OAR_SERVICES_COLLECTION_ID,
                    recordId=dist.dataservice.dataservice_id,  # ty:ignore[unresolved-attribute]
                    rel="dataservice",
                    typ=None,
                )
            )
            record.properties["externalIds"] = [dist.external_record_id(lang)]

        info_dist = featureinfo_distribution(dist.dataset, dist)
        if info_dist:
            record.links.append(
                OARRecordLink(
                    collectionId=settings.OAR_DISTRIBUTIONS_COLLECTION_ID,
                    recordId=info_dist.distribution_id,
                    rel="featureinfo",
                    typ=None,
                )
            )

        # Add style relation
        if isinstance(dist, (ExternalWMSDistribution, ExternalWMTSDistribution)):
            record.links.append(
                OASStyleLink(
                    distribution_id=dist.distribution_id,
                    rel="styledBy",
                    title="Style Hints for WMTS Raster Layer (Maplibre Style Spec)",
                )
            )

        if isinstance(dist, ExternalGeoadminFeaturesDistribution):
            if dist.renderable:
                # We use the relation `preview` here, as the HTML popup can be seen as a preview
                # or human-readable representation of the data behind the distribution.
                # htmlpopup_url = getattr(dist, f"htmlpopup_url_{lang}", None)
                htmlpopup_url_base = "https://api3.geo.admin.ch/rest/services/ech/MapServer/"
                record.linkTemplates.append(
                    LinkTemplate(
                        uriTemplate=f"{htmlpopup_url_base}{dist.external_record_id(lang)}/{{featureId}}/htmlPopup?lang={{lang}}",
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
            url = ds.localized_capabilities_url(lang)
            if "{epsg}" in url:
                record.linkTemplates.append(
                    LinkTemplate(
                        uriTemplate=url,
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
                    Link(
                        href=url,
                        rel="describedby",
                        typ="application/xml",
                        title="WMTS Capabilities File",
                    )
                )

        elif isinstance(ds, WMSDataservice):
            record.links.append(
                Link(
                    href=ds.localized_capabilities_url(lang),
                    rel="describedby",
                    typ="application/xml",
                    title="WMS Capabilities File",
                )
            )
        elif isinstance(ds, OGCAPIStacDataservice):
            record.links.append(
                Link(
                    href=ds.landing_page_url,
                    rel="describedby",
                    typ="application/json",
                    title="Landing Page of the OGC API Features/STAC Dataservice",
                )
            )
        elif isinstance(ds, GeoadminFeaturesDataservice):
            record.links.append(
                Link(
                    href=ds.landing_page_url,
                    rel="describes",
                    typ="application/json",
                    title="Root URL of the Geoadmin Features Dataservice",
                )
            )

        return record


class OAFeatureCollection(BaseModel):
    typ: str = Field(default="FeatureCollection", serialization_alias="type")
    features: list[OARDistribution | OARDataset | OARDataservice] = Field(default_factory=list)
    links: list[BaseLink] = Field(default_factory=list)
    collection_id: str = Field(exclude=True)
    lang: str = Field(default="de", exclude=True)

    @model_validator(mode="after")
    def add_links(self) -> OAFeatureCollection:
        self.links.append(
            OARCollectionItemsLink(
                collectionId=self.collection_id, rel="self", title="Link to this resource"
            )
        )
        for lang, value in LANGS.items():
            if lang != self.lang:
                self.links.append(
                    OARCollectionItemsLink(
                        collectionId=self.collection_id,
                        rel="alternate",
                        title=f"Link to this resource ({value.alternate})",
                    )
                )
        self.links.append(
            OARCollectionLink(
                collectionId=self.collection_id,
                rel="collection",
                title="Link to the collection these items belong to",
            )
        )
        return self

    def get_key(self) -> str:
        return f"/collections/{self.collection_id}/items.{self.lang}"


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
    lang: str = Field(default="de", exclude=True)
    # We don't encode records inline anymore but use the /items endpoint instead,
    # and include a link to the /items endpoint in the collection links.
    # recordsArrayName: str = "records"
    # records: list[Any] = Field(default_factory=list)
    links: list[BaseLink] = Field(default_factory=list)
    # We don't want the features field to be serialized in the collection record
    # and therefore set `exclude=True`.
    feature_collection: OAFeatureCollection = Field(
        default_factory=lambda data: OAFeatureCollection(
            collection_id=data["id"], lang=data["lang"]
        ),
        exclude=True,
    )

    @model_validator(mode="after")
    def add_links(self) -> OARCollection:
        self.links.append(
            OARCollectionItemsLink(
                collectionId=self.id, rel="items", title="Link to the items of this collection"
            )
        )
        self.links.append(
            OARCollectionLink(collectionId=self.id, rel="self", title="Link to this resource")
        )
        for lang, value in LANGS.items():
            if lang != self.lang:
                self.links.append(
                    OARCollectionLink(
                        collectionId=self.id,
                        rel="alternate",
                        title=f"Link to this resource ({value.alternate})",
                    )
                )
        return self

    def get_key(self) -> str:
        return f"/collections/{self.id}.{self.lang}"


class Contact(BaseModel):
    organization: str
    country: str
    role: str
    # name: str | None
    # position: str | None
    # email: str | None
    # phone: str | None
    # address: str | None
    # city: str | None
    # postal_code: str | None


class OASStyleLink(BaseLink):
    """Link to a Maplibre style file."""

    distribution_id: str = Field(exclude=True)

    @model_validator(mode="after")
    def generate_href_value(self) -> OASStyleLink:
        """Generate the href value for the style link.

        This method is called after the model is initialized and will set the href value
        based on the styles path prefix and the distribution_id.
        """
        self.href = f"{settings.OAS_PATH_PREFIX}/{self.distribution_id}:style"
        return self


class RasterPaint(BaseModel):
    """A Maplibre paint definition.

    See https://maplibre.org/maplibre-style-spec/layers/#paint.

    Note that raster-gutter is actually not part of the specs.
    """

    raster_opacity: float | None = Field(default=None, serialization_alias="raster-opacity")
    raster_gutter: int | None = Field(default=None, serialization_alias="raster-gutter")


class RasterLayer(BaseModel):
    """A Maplibre raster layer definition.

    See https://maplibre.org/maplibre-style-spec/layers/#layer-properties.
    """

    id: str
    paint: RasterPaint
    source: str
    type: Literal["raster"] = "raster"


class RasterStyle(BaseModel):
    """A Maplibre style file for a single raster layer.

    See https://maplibre.org/maplibre-style-spec/layers/.
    """

    id: str
    layers: list[RasterLayer] = Field(default_factory=list)
    lang: str = Field(default="de", exclude=True)

    @classmethod
    def from_distribution(
        cls,
        dist: Distribution,
        lang: str,
    ) -> RasterStyle | None:
        if not isinstance(dist, (ExternalWMSDistribution, ExternalWMTSDistribution)):
            return None

        id_ = f"{dist.distribution_id}:style"
        return RasterStyle(
            id=id_,
            layers=[
                RasterLayer(
                    id=id_,
                    paint=RasterPaint(
                        raster_opacity=dist.opacity,
                        raster_gutter=getattr(dist, "gutter", None),
                    ),
                    source=dist.dataservice.dataservice_id,
                )
            ],
            lang=lang,
        )

    def get_key(self) -> str:
        return f"/styles/{self.id}.{self.lang}"
