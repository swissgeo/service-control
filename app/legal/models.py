from django.db import models
from django.utils.translation import pgettext_lazy as _

from utils.fields import CustomSlugField


class GeopoliticalEntity(models.Model):
    """Entity model for geopolitical entities"""

    _context = "Geopolitical Entity Model"

    class Level(models.TextChoices):
        FEDERAL = "federal", _("GeopoliticalEntity Level", "Federal")
        CANTONAL = "cantonal", _("GeopoliticalEntity Level", "Cantonal")
        COMMUNAL = "communal", _("GeopoliticalEntity Level", "Communal")
        DISTRICTAL = "districtal", _("GeopoliticalEntity Level", "Districtal")
        CORPORAL = "corporal", _("GeopoliticalEntity Level", "Corporal")

    geopolitical_entity_id = CustomSlugField(
        max_length=100,
        unique=True,
        help_text=_(_context, "Stable external identifier of the geopolitical entity"),
    )
    type = models.CharField(
        max_length=255,
        choices=Level.choices,
        default=Level.COMMUNAL,
        help_text=_(_context, "Describes the type / level of geopolitical unit"),
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text=_(_context, "Link to the parent geopolitical entity"),
    )
    name_de = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_(_context, "The german name of the GeopoliticalEntity (without type)"),
    )
    name_fr = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_(_context, "The french name of the GeopoliticalEntity (without type)"),
    )
    name_it = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_(_context, "The italian name of the GeopoliticalEntity (without type)"),
    )
    name_rm = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_(_context, "The romanish name of the GeopoliticalEntity (without type)"),
    )
    abbr = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_(_context, "Abbreviation or acronym of the name"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_(_context, "Created at"),
        help_text=_(_context, "Date and time when the geopolitical entity was created"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_(_context, "Updated at"),
        help_text=_(_context, "Date and time when the geopolitical entity was last updated"),
    )

    def __str__(self) -> str:
        return str(self.geopolitical_entity_id)
