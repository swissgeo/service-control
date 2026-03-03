import logging

from django.db import models
from django.utils.translation import pgettext_lazy as _

from dataservice.models import Dataservice
from dataset.models import Dataset
from utils.fields import CustomSlugField

logger = logging.getLogger(__name__)


class Distribution(models.Model):
    _context = "Distribution Model"

    distribution_id = CustomSlugField(_(_context, "External ID"), unique=True, max_length=100)

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    dataservice = models.ForeignKey(Dataservice, on_delete=models.SET_NULL, null=True)
    title = models.CharField(_(_context, "Title"), max_length=255)
    protocol = models.CharField(_(_context, "Protocol"), max_length=32)
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

    class Meta:
        verbose_name = _("Distribution", "Distributions")
        verbose_name_plural = _("Distribution", "Distributions")

    def __str__(self) -> str:
        return self.title
