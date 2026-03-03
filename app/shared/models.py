import logging

from django.db import models
from django.template.defaultfilters import slugify
from django.utils.translation import pgettext_lazy as _

from utils.fields import CustomSlugField

logger = logging.getLogger(__name__)


class LinkManager(models.Manager):
    def get_by_natural_key(self, link_id: str) -> models.Model:
        return self.get(link_id=link_id)


class Link(models.Model):
    """Link model."""

    _context = "Link Model"

    link_id = CustomSlugField(_(_context, "External ID"), unique=True, blank=True, max_length=100)

    href = models.URLField(max_length=2048)
    rel = models.CharField(max_length=30)
    # added link_ to the fieldname, as "type" is reserved
    link_type = models.CharField(blank=True, null=True, max_length=150)
    title = models.CharField(max_length=255)
    hreflang = models.CharField(blank=True, null=True, max_length=32)

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

    objects = LinkManager()

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"{self.rel}: {self.href}"

    def save(self, *args, **kwargs) -> None:
        if not self.link_id:
            self.link_id = slugify(self.title)

        """Validate the hreflang"""
        self.full_clean()

        super().save(*args, **kwargs)

    def natural_key(self) -> tuple:
        return (self.link_id,)


class ServiceDescLink(Link):
    pass


class ServiceDocLink(Link):
    pass


class DescribesLink(Link):
    pass


class TemplateLinkManager(models.Manager):
    def get_by_natural_key(self, templatelink_id: str) -> models.Model:
        return self.get(templatelink_id=templatelink_id)


class TemplateLink(models.Model):
    """TemplateLink model."""

    _context = "TemplateLink Model"

    templatelink_id = CustomSlugField(
        _(_context, "External ID"), unique=True, blank=True, max_length=100
    )

    uri_template = models.URLField(
        max_length=2048,
        help_text=_(
            _context,
            "URI template with variables in curly braces. For example: https://example.com/datasets/{dataset_id}",
        ),
    )
    rel = models.CharField(max_length=30)
    # added link_ to the fieldname, as "type" is reserved
    link_type = models.CharField(blank=True, null=True, max_length=150)
    title = models.CharField(max_length=255)

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

    objects = TemplateLinkManager()

    def __str__(self) -> str:
        return f"{self.rel}: {self.uri_template}"

    def save(self, *args, **kwargs) -> None:
        if not self.templatelink_id:
            self.templatelink_id = slugify(self.title)

        super().save(*args, **kwargs)

    def natural_key(self) -> tuple:
        return (self.templatelink_id,)


class TemplateLinkVariableManager(models.Manager):
    def get_by_natural_key(self, variable_name: str, template_link_id: str) -> models.Model:
        return self.get(
            template_link__templatelink_id=template_link_id,
            variable_name=variable_name,
        )


class TemplateLinkVariable(models.Model):
    """TemplateLinkVariable model."""

    _context = "TemplateLinkVariable Model"

    template_link = models.ForeignKey(
        TemplateLink,
        on_delete=models.CASCADE,
        related_name="variables",
    )
    variable_name = models.CharField(
        max_length=32,
        help_text=_(_context, "Name of the variable in the URI template, without curly braces"),
    )
    variable_dict = models.JSONField(
        blank=True, null=True, help_text=_(_context, "JSON field to store the variable dictionary")
    )

    objects = TemplateLinkVariableManager()

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["template_link", "variable_name"], name="unique_variable_per_template_link"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.variable_name} (for {self.template_link})"

    def natural_key(self) -> tuple:
        return (self.variable_name,) + self.template_link.natural_key()  # noqa: RUF005, following Django docs ex.

    # According to Django docs, when using natural keys with foreign keys,
    # you need to specify the dependencies of the natural key.
    # In this case, TemplateLinkVariable depends on TemplateLink because of
    # the foreign key relationship.
    # However: ty doesn't accept this as "unresolvable attribute"
    # natural_key.dependencies = ["shared.templatelink"]  # noqa: RUF012, RUF100
