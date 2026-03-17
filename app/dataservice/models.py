import logging

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.template.defaultfilters import slugify
from django.utils.translation import pgettext_lazy as _

from utils.fields import CustomSlugField

logger = logging.getLogger(__name__)

_context = "Dataservice Module"


class DataserviceManager(models.Manager):
    def get_by_natural_key(self, dataservice_id: str) -> models.Model:
        return self.get(dataservice_id=dataservice_id)


class Dataservice(models.Model):
    """Dataservice model.

    Note: We purposely create an abstract base class here and create concrete subclasses
    for different types of dataservices (e.g. WMS, WMTS, WFS, OGC API, etc.). For once
    we want to be able to link the different distribution types to correct data service
    (e.g. a WMTS Distribution can only be part of WMTS DataService) and for another,
    we have different functionality and likely different fields for different types
    of dataservices (e.g. regarding links).
    """

    dataservice_id = CustomSlugField(_(_context, "External ID"), unique=True, max_length=100)

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

    # TODO: this is a naive implementation that checks if the object
    # has an attribute referencing the child class object.
    # A proper solution would involve using a third-party package
    # like django-polymorphic or django-model-utils, we leave it like
    # this for now to avoid adding additional dependencies and complexity
    # for now.
    def get_child_class_object(self) -> Dataservice:
        """Returns the child object of the dataservice instance."""
        for subclass in self.__class__.__subclasses__():
            try:
                return subclass.objects.get(pk=self.pk)
            except subclass.DoesNotExist:
                continue
            # This solution is possible as well but leads to more
            # complex code on usage side.
            # if hasattr(self, subclass.__name__.lower()):
            #     return getattr(self, subclass.__name__.lower())
        raise TypeError(f"no child found for dataservice with id {self.dataservice_id}")


class WMSDataservice(Dataservice):
    languages = ArrayField(
        models.CharField(
            max_length=32,
        ),
        verbose_name=_(_context, "Supported Languages"),
        help_text=_(_context, "List of supported languages for the WMS Dataservice"),
    )
    capabilities_url = models.URLField(
        _(_context, "Capabilities URL"),
        max_length=500,
        help_text=_(
            _context,
            "URL to the capabilities document of the WMS Dataservice. "
            "The URL can contain the following placeholders: {lang} for the "
            "different languages in which the WMS is available.",
        ),
    )

    class Meta:
        verbose_name = _("WMS Dataservice", "WMS Dataservices")
        verbose_name_plural = _("WMS Dataservice", "WMS Dataservices")

    @property
    def service_type(self) -> str:
        return "ogc:wms"


class WMTSDataservice(Dataservice):
    variable_epsg_list = ArrayField(
        models.IntegerField(),
        verbose_name=_(_context, "List of supported CRS (EPSG codes)"),
        help_text=_(
            _context,
            "List of the EPSG codes for the supported CRS of the WMTS Dataservice "
            "if {epsg} placeholder is used in the capabilities URL.",
        ),
    )
    capabilities_url = models.URLField(
        _(_context, "Capabilities URL"),
        max_length=500,
        help_text=_(
            _context,
            "URL to the capabilities document of the WTMS Dataservice. "
            "The URL can contain the following placeholders: {epsg} for the "
            "different supported EPSG code.",
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
        blank=True,
        null=True,
        help_text=_(_context, "URL to the landing page of the OGC API STAC Dataservice"),
    )

    class Meta:
        verbose_name = _("OGC API STAC Dataservice", "OGC API STAC Dataservices")
        verbose_name_plural = _("OGC API STAC Dataservice", "OGC API STAC Dataservices")

    @property
    def service_type(self) -> str:
        return "ogcapi:stac"


class GeoadminFeaturesDataservice(Dataservice):
    class Meta:
        verbose_name = _("Geoadmin Features Dataservice", "Geoadmin Features Dataservices")
        verbose_name_plural = _("Geoadmin Features Dataservice", "Geoadmin Features Dataservices")

    @property
    def service_type(self) -> str:
        return "geoadmin:features"
