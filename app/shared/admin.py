from typing import TYPE_CHECKING, Any

from django.contrib import admin

from .models import (
    DescribesLink,
    LinkTemplate,
    LinkTemplateVariable,
    ServiceDescLink,
    ServiceDocLink,
)

if TYPE_CHECKING:
    from django.http.request import HttpRequest


@admin.register(ServiceDescLink)
class ServiceDescLinkAdmin(admin.ModelAdmin):
    """Admin View for ServiceDescLink"""

    list_display = ("link_id", "href", "rel", "link_type")
    readonly_fields = ("created_at", "updated_at", "link_id")


@admin.register(ServiceDocLink)
class ServiceDocLinkAdmin(admin.ModelAdmin):
    """Admin View for ServiceDocLink"""

    list_display = ("link_id", "href", "rel", "link_type")
    readonly_fields = ("created_at", "updated_at", "link_id")


@admin.register(DescribesLink)
class DescribesLinkAdmin(admin.ModelAdmin):
    """Admin View for DescribesLink"""

    list_display = ("link_id", "href", "rel", "link_type")
    readonly_fields = ("created_at", "updated_at", "link_id")


class LinkTemplateVariableInline(admin.TabularInline):
    """Inline admin for LinkTemplateVariable"""

    model = LinkTemplateVariable
    extra = 1
    fields = ("variable_name", "variable_dict")


@admin.register(LinkTemplate)
class LinkTemplateAdmin(admin.ModelAdmin):
    """Admin View for LinkTemplate"""

    list_display = ("linktemplate_id", "uri_template", "rel", "link_type")
    readonly_fields = ("created_at", "updated_at", "linktemplate_id")
    inlines = [LinkTemplateVariableInline]  # noqa: RUF012

    def get_readonly_fields(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Link id cannot be updated
            return (*self.readonly_fields, "templatelink_id")
        return self.readonly_fields
