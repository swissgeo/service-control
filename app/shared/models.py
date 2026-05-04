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
    class Meta:
        proxy = True


class ServiceDocLink(Link):
    class Meta:
        proxy = True


class DescribesLink(Link):
    class Meta:
        proxy = True


class LinkTemplateManager(models.Manager):
    def get_by_natural_key(self, linktemplate_id: str) -> models.Model:
        return self.get(linktemplate_id=linktemplate_id)


class LinkTemplate(models.Model):
    """LinkTemplate model."""

    _context = "LinkTemplate Model"

    linktemplate_id = CustomSlugField(
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

    objects = LinkTemplateManager()

    def __str__(self) -> str:
        return f"{self.rel}: {self.uri_template}"

    def save(self, *args, **kwargs) -> None:
        if not self.linktemplate_id:
            self.linktemplate_id = slugify(self.title)

        super().save(*args, **kwargs)

    def natural_key(self) -> tuple:
        return (self.linktemplate_id,)


class LinkTemplateVariableManager(models.Manager):
    def get_by_natural_key(self, variable_name: str, linktemplate_id: str) -> models.Model:
        return self.get(
            linktemplate__linktemplate_id=linktemplate_id,
            variable_name=variable_name,
        )


class LinkTemplateVariable(models.Model):
    """LinkTemplateVariable model."""

    _context = "LinkTemplateVariable Model"

    linktemplate = models.ForeignKey(
        LinkTemplate,
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

    objects = LinkTemplateVariableManager()

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["linktemplate", "variable_name"], name="unique_variable_per_linktemplate"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.variable_name} (for {self.linktemplate})"

    def natural_key(self) -> tuple:
        return (self.variable_name,) + self.linktemplate.natural_key()  # noqa: RUF005, following Django docs ex.

    # According to Django docs, when using natural keys with foreign keys,
    # you need to specify the dependencies of the natural key.
    # In this case, LinkTemplateVariable depends on LinkTemplate because of
    # the foreign key relationship.
    natural_key.dependencies = ["shared.linktemplate"]  # noqa: RUF012, RUF100  # ty:ignore[unresolved-attribute]
