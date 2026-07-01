from django.db import models
from django.utils.translation import pgettext_lazy as _


class GeopoliticalEntity(models.Model):
    """Entity model for geobasisdaten.ch entities"""

    _context = "Geopolitical Entity Model"

    class Level(models.TextChoices):
        FEDERAL = "federal", _("GeopoliticalEntity Level", "Federal")
        CANTON = "canton", _("GeopoliticalEntity Level", "Canton")
        COMMUNITY = "community", _("GeopoliticalEntity Level", "Community")
        REGION = "region", _("GeopoliticalEntity Level", "Region")
        COUNTY = "county", _("GeopoliticalEntity Level", "County")
        CORP = "corp", _("GeopoliticalEntity Level", "Corporate")

    geopolitical_entity_id = models.IntegerField(
        unique=True, help_text=_(_context, "Stable external identifier of the geopolitical entity")
    )
    type = models.CharField(
        max_length=255,
        choices=Level.choices,
        default=Level.COMMUNITY,
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
    name = models.CharField(
        max_length=255, help_text=_(_context, "The name of the GeopoliticalEntity (without type)")
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
        return self.name
