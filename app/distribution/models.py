import logging
from typing import ClassVar

from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import pgettext_lazy as _

from dataservice.models import OGCAPIStacDataservice, WMSDataservice, WMTSDataservice
from dataset.models import Dataset
from utils.fields import CustomSlugField

logger = logging.getLogger(__name__)

_context = "Distribution Model"


class Distribution(PolymorphicModel):
    """Abstract Base Distribution model."""

    # TODO: should this identifier be globally unique or just unique per dataset?
    distribution_id = CustomSlugField(_(_context, "External ID"), unique=True, max_length=100)

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    title = models.CharField(_(_context, "Title"), max_length=255)

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
        return self.title


class ExternalDistribution(Distribution):
    """Distribution model for external distributions."""

    class Meta:
        abstract = True
        verbose_name = _(_context, "External Distributions")
        verbose_name_plural = _(_context, "External Distributions")


class ExternalWMSDistribution(ExternalDistribution):
    """Distribution model for external WMS distributions."""

    dataservice = models.ForeignKey(WMSDataservice, on_delete=models.SET_NULL, null=True)
    wms_layer_name = models.CharField(_(_context, "WMS Layer Name"), max_length=255)
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
                fields=["dataservice", "wms_layer_name"],
                name="unique_wms_layer_name_per_dataservice",
            ),
        ]
        verbose_name = _(_context, "External WMS Distributions")
        verbose_name_plural = _(_context, "External WMS Distributions")


class ExternalWMTSDistribution(ExternalDistribution):
    """Distribution model for external WMTS distributions."""

    dataservice = models.ForeignKey(WMTSDataservice, on_delete=models.SET_NULL, null=True)
    wmts_layer_name = models.CharField(_(_context, "WMTS Layer Name"), max_length=255)
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
                fields=["dataservice", "wmts_layer_name"],
                name="unique_wmts_layer_name_per_dataservice",
            ),
        ]
        verbose_name = _(_context, "External WMTS Distributions")
        verbose_name_plural = _(_context, "External WMTS Distributions")


class ExternalStacDistribution(ExternalDistribution):
    """Distribution model for external STAC distributions."""

    dataservice = models.ForeignKey(OGCAPIStacDataservice, on_delete=models.SET_NULL, null=True)
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
