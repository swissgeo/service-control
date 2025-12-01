from utils.fields import CustomSlugField

from django.db import models
from django.utils.translation import pgettext_lazy as _


class Organization(models.Model):

    _context = "Organization model"

    def __str__(self) -> str:
        return str(self.organization_id)

    '''
    Note: The "blank=False" for a model field doesn't prevent DB changes.
          It only has an effect on form validation.
    '''
    organization_id = CustomSlugField(
        _(_context, "External ID"), max_length=100, unique=True, db_index=True
    )
    created = models.DateTimeField(_(_context, "Created"), auto_now_add=True)
    updated = models.DateTimeField(_(_context, "Updated"), auto_now=True)

    name_de = models.CharField(_(_context, "Name (German)"))
    name_fr = models.CharField(_(_context, "Name (French)"))
    name_en = models.CharField(_(_context, "Name (English)"))
    name_it = models.CharField(_(_context, "Name (Italian)"), null=True, blank=True)
    name_rm = models.CharField(_(_context, "Name (Romansh)"), null=True, blank=True)

    acronym_de = models.CharField(_(_context, "Acronym (German)"))
    acronym_fr = models.CharField(_(_context, "Acronym (French)"))
    acronym_en = models.CharField(_(_context, "Acronym (English)"))
    acronym_it = models.CharField(_(_context, "Acronym (Italian)"), null=True, blank=True)
    acronym_rm = models.CharField(_(_context, "Acronym (Romansh)"), null=True, blank=True)
