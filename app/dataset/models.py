import logging

from django.db import models
from django.utils.translation import pgettext_lazy as _

from utils.fields import CustomSlugField

logger = logging.getLogger(__name__)


class Dataset(models.Model):
    """Dataset model."""

    _context = "Dataset Model"

    dataset_id = CustomSlugField(_(_context, "External ID"), unique=True, max_length=100)

    # The title we currently harvest from BOD and store here is actually a short
    # version of the original title. In a later iteration, we'll add the original
    # title as well.
    title_short_de = models.CharField(_(_context, "Title (German)"))
    title_short_fr = models.CharField(_(_context, "Title (French)"))
    title_short_en = models.CharField(_(_context, "Title (English)"))
    title_short_it = models.CharField(_(_context, "Title (Italian)"), null=True, blank=True)
    title_short_rm = models.CharField(_(_context, "Title (Romansh)"), null=True, blank=True)

    description_de = models.TextField(_(_context, "Description (German)"))
    description_fr = models.TextField(_(_context, "Description (French)"))
    description_en = models.TextField(_(_context, "Description (English)"))
    description_it = models.TextField(_(_context, "Description (Italian)"), null=True, blank=True)
    description_rm = models.TextField(_(_context, "Description (Romansh)"), null=True, blank=True)

    geocat_id = models.CharField(_(_context, "Geocat ID"), unique=True, max_length=100)

    preferred_distribution = models.ForeignKey(
        "distribution.Distribution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_for_datasets",
    )

    keywords = models.ManyToManyField("thesaurus.Keyword", related_name="keywords", blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_(_context, "Created at"),
        help_text=_(_context, "Date and time when the dataset was created"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_(_context, "Updated at"),
        help_text=_(_context, "Date and time when the dataset was last updated"),
    )

    class Meta:
        verbose_name = _("Dataset Model", "Dataset")
        verbose_name_plural = _("Dataset Model", "Datasets")

    def __str__(self) -> str:
        return self.dataset_id
