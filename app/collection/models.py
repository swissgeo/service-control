import logging

from django.db import models
from django.utils.translation import pgettext_lazy as _

from utils.fields import CustomSlugField

logger = logging.getLogger(__name__)


class Collection(models.Model):
    """Collection model."""

    _context = "Collection Model"

    # TODO: should this identifier be globally unique or just unique per dataset?
    collection_id = CustomSlugField(_(_context, "External ID"), unique=True, max_length=100)

    dataset = models.ForeignKey("dataset.Dataset", on_delete=models.CASCADE)
    title_de = models.CharField(_(_context, "Title (German)"), max_length=255)
    title_fr = models.CharField(
        _(_context, "Title (French)"), null=True, blank=True, max_length=255
    )
    title_en = models.CharField(
        _(_context, "Title (English)"), null=True, blank=True, max_length=255
    )
    title_it = models.CharField(
        _(_context, "Title (Italian)"), null=True, blank=True, max_length=255
    )
    title_rm = models.CharField(
        _(_context, "Title (Romansh)"), null=True, blank=True, max_length=255
    )

    description_de = models.TextField(_(_context, "Description (German)"), null=True, blank=True)
    description_fr = models.TextField(_(_context, "Description (French)"), null=True, blank=True)
    description_en = models.TextField(_(_context, "Description (English)"), null=True, blank=True)
    description_it = models.TextField(_(_context, "Description (Italian)"), null=True, blank=True)
    description_rm = models.TextField(_(_context, "Description (Romansh)"), null=True, blank=True)

    meta_information = models.BooleanField(
        _(_context, "Meta Information"),
        default=False,
        help_text=_(_context, "Whether the layer holds meta information (rather than data)"),
    )

    class DataSource(models.TextChoices):
        BOD_LAYERS_JS = "bod-layers-js", _("Collection DataSource", "BOD (Layers JS)")
        SERVICE_CAPABILITIES = (
            "service-capabilities",
            _(
                "Collection DataSource",
                "Service Capabilities (e.g. WMS GetCapabilities, STAC API)",
            ),
        )
        USER_INPUT = "user-input", _("Collection DataSource", "User Input (Via Admin Interface)")

    data_source = models.CharField(
        _(_context, "Data Source"), choices=DataSource.choices, max_length=255
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_(_context, "Created at"),
        help_text=_(_context, "Date and time when the collection was created"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_(_context, "Updated at"),
        help_text=_(_context, "Date and time when the collection was last updated"),
    )

    class Meta:
        verbose_name = _("Collection", "Collections")
        verbose_name_plural = _("Collection", "Collections")

    def __str__(self) -> str:
        return self.collection_id
