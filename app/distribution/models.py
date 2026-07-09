import logging
from abc import abstractmethod
from typing import ClassVar

from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import pgettext_lazy as _

from utils.fields import CustomSlugField

logger = logging.getLogger(__name__)

_context = "Distribution Model"


class Distribution(PolymorphicModel):
    """Abstract Base Distribution model."""

    # TODO: should this identifier be globally unique or just unique per dataset?
    distribution_id = CustomSlugField(_(_context, "External ID"), unique=True, max_length=100)

    dataset = models.ForeignKey("dataset.Dataset", on_delete=models.CASCADE)
    title = models.CharField(_(_context, "Title"), max_length=255)

    class DataSource(models.TextChoices):
        BOD_LAYERS_JS = "bod-layers-js", _("Distribution DataSource", "BOD (Layers JS)")
        SERVICE_CAPABILITIES = (
            "service-capabilities",
            _(
                "Distribution DataSource",
                "Service Capabilities (e.g. WMS GetCapabilities, STAC API)",
            ),
        )
        USER_INPUT = "user-input", _("Distribution DataSource", "User Input (Via Admin Interface)")

    data_source = models.CharField(
        _(_context, "Data Source"), choices=DataSource.choices, max_length=255
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_(_context, "Created at"),
        help_text=_(_context, "Date and time when the distribution was created"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_(_context, "Updated at"),
        help_text=_(_context, "Date and time when the distribution was last updated"),
    )

    objects = PolymorphicManager()

    class Meta:
        verbose_name = _("Distribution", "Distributions")
        verbose_name_plural = _("Distribution", "Distributions")

    def __str__(self) -> str:
        return self.distribution_id

    @property
    @abstractmethod
    def protocol(self) -> str:
        """Protocol of the distribution, e.g. WMS, WMTS, STAC API, GeoJSON, etc."""
        raise NotImplementedError(
            "The 'protocol' property must be implemented in concrete Distribution subclasses."
        )

    @abstractmethod
    def external_record_id(self, lang: str) -> str:
        """The identifier of the distribution, as used in the data service."""
        raise NotImplementedError(
            "The 'external_record_id' property must be implemented in concrete Distribution "
            "subclasses."
        )


class ExternalDistribution(Distribution):
    """Distribution model for external distributions."""

    class Meta:
        abstract = True
        verbose_name = _(_context, "External Distributions")
        verbose_name_plural = _(_context, "External Distributions")


class ExternalWMSDistribution(ExternalDistribution):
    """Distribution model for external WMS distributions."""

    dataservice = models.ForeignKey(
        "dataservice.WMSDataservice", on_delete=models.SET_NULL, null=True
    )
    wms_layer_name_de = models.CharField(_(_context, "WMS Layer Name (default/DE)"), max_length=255)
    wms_layer_name_fr = models.CharField(
        _(_context, "WMS Layer Name (FR)"), max_length=255, null=True, blank=True
    )
    wms_layer_name_en = models.CharField(
        _(_context, "WMS Layer Name (EN)"), max_length=255, null=True, blank=True
    )
    wms_layer_name_it = models.CharField(
        _(_context, "WMS Layer Name (IT)"), max_length=255, null=True, blank=True
    )
    wms_layer_name_rm = models.CharField(
        _(_context, "WMS Layer Name (RM)"), max_length=255, null=True, blank=True
    )
    opacity = models.DecimalField(
        _(_context, "Opacity"),
        default=1.0,
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_(_context, "Desired Opacity of the WMS layer when displayed in web app."),
    )
    gutter = models.PositiveSmallIntegerField(
        _(_context, "Gutter"),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(500)],
        help_text=_(_context, "Desired Gutter of the WMS layer when using tiled in web app."),
    )

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["dataservice", "wms_layer_name_de"],
                name="unique_wms_layer_name_per_dataservice",
            ),
        ]
        verbose_name = _(_context, "External WMS Distributions")
        verbose_name_plural = _(_context, "External WMS Distributions")

    @property
    def protocol(self) -> str:
        return "ogc:wms"

    def external_record_id(self, lang: str) -> str:
        default = self.wms_layer_name_de
        return getattr(self, f"wms_layer_name_{lang}", default) or default


class ExternalWMTSDistribution(ExternalDistribution):
    """Distribution model for external WMTS distributions."""

    dataservice = models.ForeignKey(
        "dataservice.WMTSDataservice", on_delete=models.SET_NULL, null=True
    )
    wmts_layer_name_de = models.CharField(
        _(_context, "WMTS Layer Name (default/DE)"), max_length=255
    )
    wmts_layer_name_fr = models.CharField(
        _(_context, "WMTS Layer Name (FR)"), max_length=255, null=True, blank=True
    )
    wmts_layer_name_en = models.CharField(
        _(_context, "WMTS Layer Name (EN)"), max_length=255, null=True, blank=True
    )
    wmts_layer_name_it = models.CharField(
        _(_context, "WMTS Layer Name (IT)"), max_length=255, null=True, blank=True
    )
    wmts_layer_name_rm = models.CharField(
        _(_context, "WMTS Layer Name (RM)"), max_length=255, null=True, blank=True
    )
    opacity = models.DecimalField(
        _(_context, "Opacity"),
        default=1.0,
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_(_context, "Desired Opacity of the WMTS layer when displayed in web app."),
    )

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["dataservice", "wmts_layer_name_de"],
                name="unique_wmts_layer_name_per_dataservice",
            ),
        ]
        verbose_name = _(_context, "External WMTS Distributions")
        verbose_name_plural = _(_context, "External WMTS Distributions")

    @property
    def protocol(self) -> str:
        return "ogc:wmts"

    def external_record_id(self, lang: str) -> str:
        default = self.wmts_layer_name_de
        return getattr(self, f"wmts_layer_name_{lang}", default) or default


class ExternalStacDistribution(ExternalDistribution):
    """Distribution model for external STAC distributions."""

    dataservice = models.ForeignKey(
        "dataservice.OGCAPIStacDataservice", on_delete=models.SET_NULL, null=True
    )
    stac_collection_id = models.CharField(_(_context, "STAC Collection ID"), max_length=255)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["dataservice", "stac_collection_id"],
                name="unique_stac_collection_id_per_dataservice",
            ),
        ]
        verbose_name = _(_context, "External STAC Distributions")
        verbose_name_plural = _(_context, "External STAC Distributions")

    @property
    def protocol(self) -> str:
        return "ogcapi:stac"

    def external_record_id(self, lang: str) -> str:
        return self.stac_collection_id


class ExternalGeoJSONDistribution(ExternalDistribution):
    """Distribution model for external GeoJSON distributions.

    TODO/TO BE DISCUSSED: Currently GeoJSON Distributions don't have a reference to a dataservice,
    they just have a link to the actual file. This requires different handling of GeoJSON
    distributions in several places. We could model GeoJSON distributions with a somewhat generic
    "dataservice", which would just be the base URL of the GeoJSON file, and then we could have
    multiple distributions referencing the same "dataservice" with different language-specific URIs
    (without the domain) that would be the 'externalIds'.
    This would make handling of GeoJSON distributions more consistent with other distribution
    types.
    """

    geojson_url_de = models.URLField(_(_context, "GeoJSON URL (DE)"), max_length=2048)
    geojson_url_fr = models.URLField(
        _(_context, "GeoJSON URL (FR)"), max_length=2048, null=True, blank=True
    )
    geojson_url_it = models.URLField(
        _(_context, "GeoJSON URL (IT)"), max_length=2048, null=True, blank=True
    )
    geojson_url_en = models.URLField(
        _(_context, "GeoJSON URL (EN)"), max_length=2048, null=True, blank=True
    )
    geojson_url_rm = models.URLField(
        _(_context, "GeoJSON URL (RM)"), max_length=2048, null=True, blank=True
    )
    style_url = models.URLField(
        _(_context, "Style URL"),
        max_length=2048,
        null=True,
        blank=True,
        help_text=_(_context, "Optional URL to a style file for the GeoJSON layer."),
    )

    class Meta:
        verbose_name = _(_context, "External GeoJSON Distributions")
        verbose_name_plural = _(_context, "External GeoJSON Distributions")

    @property
    def protocol(self) -> str:
        return "geojson"

    def external_record_id(self, lang: str) -> str:
        # TODO: This is probably not correct. In case of Swisstopo distributions with URLs like
        # https://data.geo.admin.ch/ch.bfe.shared-mobility/ch.bfe.shared-mobility_de.json
        # and style URS likes
        # https://api3.geo.admin.ch/static/vectorStyles/ch.bfe.shared-mobility.json
        # the external ID should probably be "ch.bfe.shared-mobility".
        # This is no problem ATM, as this is never used in case of GeoJSON distributions (see also
        # comment above regarding distributions and the one in in export_models regarding exporting
        # distributions). But it might be better, to switch for example to a template mechanism
        # like in the dataservices.
        default = self.geojson_url_de
        return getattr(self, f"geojson_url_{lang}", default) or default


class ExternalGeoadminFeaturesDistribution(ExternalDistribution):
    """Distribution model for geoadmin features (aka api3/identify) distributions."""

    dataservice = models.ForeignKey(
        "dataservice.GeoadminFeaturesDataservice", on_delete=models.SET_NULL, null=True
    )
    layer_id = models.CharField(_(_context, "Geoadmin Features Layer ID"), max_length=255)
    queryable = models.BooleanField(
        _(_context, "Queryable"),
        default=True,
        help_text=_(
            _context, "Whether the layer is queryable (i.e. can be used in identify requests)"
        ),
    )
    renderable = models.BooleanField(
        _(_context, "Renderable"),
        default=True,
        help_text=_(_context, "Whether the layer is renderable (i.e. has a html tooltip)"),
    )

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["dataservice", "layer_id"],
                name="unique_layer_id_per_dataservice",
            ),
        ]
        verbose_name = _(_context, "External Geoadmin Features Distributions")
        verbose_name_plural = _(_context, "External Geoadmin Features Distributions")

    @property
    def protocol(self) -> str:
        return "geoadmin:features"

    def external_record_id(self, lang: str) -> str:
        return self.layer_id
