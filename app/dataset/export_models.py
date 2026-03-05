from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, Field

if TYPE_CHECKING:
    from dataservice.models import Dataservice
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


class Link(BaseModel):
    href: Annotated[str, AfterValidator(is_url)]
    rel: str
    title: str | None = None
    typ: str | None = Field(default=None, serialization_alias="type")
    hreflang: str | None = None


class LinkTemplate(BaseModel):
    uriTemplate: str  # noqa: N815
    rel: str
    title: str | None = None
    typ: str | None = Field(default=None, serialization_alias="type")
    variables: dict | None = None


class OARRecord(BaseModel):
    id: str
    links: list[Link] = Field(default_factory=list)
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


class OARDataservice(OARRecord):
    """Service record

    A Service is a Record with type="Service"
    """

    properties: dict = {}

    @classmethod
    def from_dataservice(cls, ds: Dataservice, lang: str = "de") -> OARDataservice:  # noqa: ARG003
        record = OARDataservice(id=ds.dataservice_id)

        # Set properties
        record.properties["title"] = getattr(ds, "title", None)
        record.properties["type"] = getattr(ds, "type", None)

        # Add links
        if ds.service_doc:
            record.links.append(
                Link(
                    href=ds.service_doc.href,
                    rel=ds.service_doc.rel,
                    typ=ds.service_doc.link_type,
                    title=ds.service_doc.title,
                )
            )
        if ds.service_desc:
            record.links.append(
                Link(
                    href=ds.service_desc.href,
                    rel=ds.service_desc.rel,
                    typ=ds.service_desc.link_type,
                    title=ds.service_desc.title,
                )
            )
        if ds.describes:
            record.links.append(
                Link(
                    href=ds.describes.href,
                    rel=ds.describes.rel,
                    typ=ds.describes.link_type,
                    title=ds.describes.title,
                )
            )
        for template_link in ds.linktemplates.all():
            record.linkTemplates.append(
                LinkTemplate(
                    uriTemplate=template_link.uri_template,
                    rel=template_link.rel,
                    typ=template_link.link_type,
                    title=template_link.title,
                    variables=dict(
                        template_link.variables.all().values_list("variable_name", "variable_dict")
                    ),
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


class Contact(BaseModel):
    organisation: str
    country: str
    role: str
    # name: Optional[str] = None
    # position: Optional[str] = None
    # email: Optional[str] = None
    # phone: Optional[str] = None
    # address: Optional[str] = None
    # city: Optional[str] = None
    # postal_code: Optional[str] = None
