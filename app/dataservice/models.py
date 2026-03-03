import logging
from typing import ClassVar

from django.db import models
from django.template.defaultfilters import slugify
from django.utils.translation import pgettext_lazy as _

from utils.fields import CustomSlugField

logger = logging.getLogger(__name__)


class DataserviceManager(models.Manager):
    def get_by_natural_key(self, dataservice_id: str) -> models.Model:
        return self.get(dataservice_id=dataservice_id)


class Dataservice(models.Model):
    """Dataservice model.

    Note: Probably it'll make sense to make this class abstract and subclass for different
    types of dataservices (e.g. WMS, WMTS, WFS, OGC API, etc.) allowing for more specific
    implementations (e.g. regarding links). But for now, we'll keep it
    simple and add a "type" field to distinguish between different types of dataservices.
    """

    _context = "Dataservice Model"

    dataservice_id = CustomSlugField(_(_context, "External ID"), unique=True, max_length=100)

    TYPE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("ogc:wms", "ogc:wms"),
        ("ogc:wmts", "ogc:wmts"),
        ("ogc:wfs", "ogc:wfs"),
        ("ogcapi:features", "ogcapi:features"),
        ("ogcapi:stac", "ogcapi:stac"),
        ("geoadmin:features", "geoadmin:features"),
    ]
    type = models.CharField(_(_context, "Type"), max_length=32, choices=TYPE_CHOICES)
    title = models.CharField(_(_context, "Title"), max_length=128)
    service_desc = models.ForeignKey(
        "shared.ServiceDescLink", on_delete=models.SET_NULL, null=True, blank=True
    )
    service_doc = models.ForeignKey(
        "shared.ServiceDocLink", on_delete=models.SET_NULL, null=True, blank=True
    )
    describes = models.ForeignKey(
        "shared.DescribesLink", on_delete=models.SET_NULL, null=True, blank=True
    )
    templated_links = models.ManyToManyField("shared.TemplateLink", blank=True)

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
