import logging

from django.db import models
from django.utils.translation import pgettext_lazy as _

logger = logging.getLogger(__name__)


class Thesaurus(models.Model):
    """Thesaurus model."""

    _context = "Thesaurus Model"

    thesaurus_id = models.CharField(_(_context, "External ID"), unique=True, max_length=200)

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_(_context, "Created at"),
        help_text=_(_context, "Date and time when the thesaurus was created"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_(_context, "Updated at"),
        help_text=_(_context, "Date and time when the thesaurus was last updated"),
    )

    class Meta:
        verbose_name_plural = "thesauri"
        ordering = ("thesaurus_id",)

    def __str__(self) -> str:
        return str(self.thesaurus_id)


class Keyword(models.Model):
    """Thesaurus model."""

    _context = "Keyword Model"

    thesaurus = models.ForeignKey(
        Thesaurus,
        on_delete=models.CASCADE,
    )

    keyword_id = models.CharField(_(_context, "External ID"), max_length=200)

    label_de = models.CharField(_(_context, "Label (German)"))
    label_fr = models.CharField(_(_context, "Label (French)"))
    label_en = models.CharField(_(_context, "Label (English)"))
    label_it = models.CharField(_(_context, "Label (Italian)"), null=True, blank=True)
    label_rm = models.CharField(_(_context, "Label (Romansh)"), null=True, blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_(_context, "Created at"),
        help_text=_(_context, "Date and time when the thesaurus was created"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_(_context, "Updated at"),
        help_text=_(_context, "Date and time when the thesaurus was last updated"),
    )

    class Meta:
        ordering = ("thesaurus__thesaurus_id", "label_en")
        constraints = (
            models.UniqueConstraint(
                fields=("thesaurus", "keyword_id"),
                name="unique_keyword_id_per_thesaurus",
            ),
        )

    def __str__(self) -> str:
        return f"{self.thesaurus.thesaurus_id}: {self.label_en}"
