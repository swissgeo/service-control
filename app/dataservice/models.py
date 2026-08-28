import logging

from iso639 import Lang
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.template.defaultfilters import slugify
from django.utils.translation import pgettext_lazy as _

from utils.fields import CustomSlugField
from utils.model import DataSourceIdManagerMixin, DataSourceIdModelMixin

logger = logging.getLogger(__name__)

_context = "Dataservice Module"


class DataserviceManager(DataSourceIdManagerMixin, PolymorphicManager):
    def get_by_natural_key(self, dataservice_id: str) -> models.Model:
        return self.get(dataservice_id=dataservice_id)


class Dataservice(DataSourceIdModelMixin, PolymorphicModel):
    """Dataservice model."""

    dataservice_id = CustomSlugField(_(_context, "External ID"), unique=True, max_length=100)

    class DataSource(models.TextChoices):
        USER_INPUT = "user-input", _("Dataservice DataSource", "User Input (Via Admin Interface)")
        GEODIENSTE = "geodienste", _("Dataservice DataSource", "geodienste.ch")

    data_source = models.CharField(
        _(_context, "Data Source"),
        choices=DataSource.choices,
        default=DataSource.USER_INPUT,
        max_length=255,
    )
    data_source_ids = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        verbose_name=_(_context, "Original IDs"),
        help_text=_(_context, "List of original external IDs"),
    )

    title = models.CharField(_(_context, "Title"), max_length=128)
    openapi_spec_url = models.URLField(
        _(_context, "OpenAPI Specification URL"),
        max_length=500,
        blank=True,
        null=True,
    )
    documentation_url_de = models.URLField(
        _(_context, "Documentation URL (DE)"),
        max_length=500,
        blank=True,
        null=True,
    )
    documentation_url_fr = models.URLField(
        _(_context, "Documentation URL (FR)"),
        max_length=500,
        blank=True,
        null=True,
    )
    documentation_url_en = models.URLField(
        _(_context, "Documentation URL (EN)"),
        max_length=500,
        blank=True,
        null=True,
    )
    documentation_url_it = models.URLField(
        _(_context, "Documentation URL (IT)"),
        max_length=500,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_(_context, "Created at"),
        help_text=_(_context, "Date and time when the dataservice was created"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_(_context, "Updated at"),
        help_text=_(_context, "Date and time when the dataservice was last updated"),
    )

    objects = DataserviceManager()

    class Meta:
        verbose_name = _("Dataservice Model", "Dataservice")
        verbose_name_plural = _("Dataservice Model", "Dataservices")

    def __str__(self) -> str:
        return self.dataservice_id

    def save(self, *args, **kwargs) -> None:
        if not self.dataservice_id:
            self.dataservice_id = slugify(self.title)

        super().save(*args, **kwargs)

    def natural_key(self) -> tuple:
        return (self.dataservice_id,)

    @property
    def service_type(self) -> str:
        raise NotImplementedError(
            "Subclasses of Dataservice must implement the service_type property"
        )


class LocalizedCapabilitiesUrlMixin:
    capabilities_url: str
    languages: list[str]
    default_language: str | None

    def localized_capabilities_url(self, requested: str) -> str:
        """Returns the capabilities URL for the requested language.

        Expects a 2 letter ISO 639-1 code.

        Only tries to interpolate the language, if the URL contains the {lang}
        (for 2 letter ISO 639-1) or {lang3} (for 3 letter ISO 639-3) placeholder.

        Uses the given language if supported, falls back to the default language.
        """

        url = self.capabilities_url
        lang = requested if requested in self.languages else (self.default_language or "")
        if "{lang}" in url:
            url = url.replace("{lang}", lang)
        if "{lang3}" in url:
            lang = Lang(pt1=lang).pt3 if lang else ""
            url = url.replace("{lang3}", lang)
        return url


class WMSDataservice(LocalizedCapabilitiesUrlMixin, Dataservice):
    languages = ArrayField(
        models.CharField(
            max_length=32,
        ),
        default=list,
        blank=True,
        verbose_name=_(_context, "Supported Languages"),
        help_text=_(
            _context, "List of supported languages (2 letter ISO 639-1) for the WMS Dataservice"
        ),
    )
    default_language = models.CharField(
        _(_context, "Default languages (2 letter ISO 639-1)"), max_length=2, blank=True, null=True
    )
    capabilities_url = models.URLField(
        _(_context, "Capabilities URL"),
        max_length=500,
        help_text=_(
            _context,
            "URL to the capabilities document of the WMS Dataservice. "
            "The URL can contain the following placeholders: {lang} (2 letter ISO 639-1) or "
            "{lang3} (3 letter ISO 639-3) for the different languages in which the WMS is "
            "available.",
        ),
    )

    class Meta:
        verbose_name = _("WMS Dataservice", "WMS Dataservices")
        verbose_name_plural = _("WMS Dataservice", "WMS Dataservices")

    @property
    def service_type(self) -> str:
        return "ogc:wms"


class WMTSDataservice(LocalizedCapabilitiesUrlMixin, Dataservice):
    variable_epsg_list = ArrayField(
        models.IntegerField(),
        verbose_name=_(_context, "List of supported CRS (EPSG codes)"),
        help_text=_(
            _context,
            "List of the EPSG codes for the supported CRS of the WMTS Dataservice "
            "if {epsg} placeholder is used in the capabilities URL.",
        ),
    )
    languages = ArrayField(
        models.CharField(
            max_length=32,
        ),
        default=list,
        blank=True,
        verbose_name=_(_context, "Supported Languages"),
        help_text=_(
            _context, "List of supported languages (2 letter ISO 639-1) for the WMS Dataservice"
        ),
    )
    default_language = models.CharField(
        _(_context, "Default languages (2 letter ISO 639-1)"),
        max_length=2,
        null=True,
        blank=True,
    )
    capabilities_url = models.URLField(
        _(_context, "Capabilities URL"),
        max_length=500,
        help_text=_(
            _context,
            "URL to the capabilities document of the WTMS Dataservice. "
            "The URL can contain the following placeholders: {epsg} for the "
            "different supported EPSG code; {lang} for the different languages "
            "in which the WMS is available.",
        ),
    )

    class Meta:
        verbose_name = _("WMTS Dataservice", "WMTS Dataservices")
        verbose_name_plural = _("WMTS Dataservice", "WMTS Dataservices")

    @property
    def service_type(self) -> str:
        return "ogc:wmts"


class WFSDataservice(Dataservice):
    class Meta:
        verbose_name = _("WFS Dataservice", "WFS Dataservices")
        verbose_name_plural = _("WFS Dataservice", "WFS Dataservices")

    @property
    def service_type(self) -> str:
        return "ogc:wfs"


class OGCAPIFeaturesDataservice(Dataservice):
    class Meta:
        verbose_name = _("OGC API Features Dataservice", "OGC API Features Dataservices")
        verbose_name_plural = _("OGC API Features Dataservice", "OGC API Features Dataservices")

    @property
    def service_type(self) -> str:
        return "ogcapi:features"


class OGCAPIStacDataservice(Dataservice):
    landing_page_url = models.URLField(
        _(_context, "Landing Page URL"),
        max_length=500,
        help_text=_(_context, "URL to the landing page of the OGC API STAC Dataservice"),
    )

    class Meta:
        verbose_name = _("OGC API STAC Dataservice", "OGC API STAC Dataservices")
        verbose_name_plural = _("OGC API STAC Dataservice", "OGC API STAC Dataservices")

    @property
    def service_type(self) -> str:
        return "ogcapi:stac"


class GeoadminFeaturesDataservice(Dataservice):
    landing_page_url = models.URLField(
        _(_context, "Landing Page URL"),
        max_length=500,
        default="https://api3.geo.admin.ch/rest/services/ech/MapServer",
        help_text=_(
            _context,
            "URL to the landing page of the geoadmin features Dataservice (e.g. "
            "'https://api3.geo.admin.ch/rest/services/ech/MapServer')",
        ),
    )

    class Meta:
        verbose_name = _("Geoadmin Features Dataservice", "Geoadmin Features Dataservices")
        verbose_name_plural = _("Geoadmin Features Dataservice", "Geoadmin Features Dataservices")

    @property
    def service_type(self) -> str:
        return "geoadmin:features"
