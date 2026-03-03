from typing import TYPE_CHECKING, Any

from django.contrib import admin

from .models import (
    DescribesLink,
    ServiceDescLink,
    ServiceDocLink,
    TemplateLink,
    TemplateLinkVariable,
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


class TemplateLinkVariableInline(admin.TabularInline):
    """Inline admin for TemplateLinkVariable"""

    model = TemplateLinkVariable
    extra = 1
    fields = ("variable_name", "variable_dict")


@admin.register(TemplateLink)
class TemplateLinkAdmin(admin.ModelAdmin):
    """Admin View for TemplateLink"""

    list_display = ("templatelink_id", "uri_template", "rel", "link_type")
    readonly_fields = ("created_at", "updated_at", "templatelink_id")
    inlines = [TemplateLinkVariableInline]  # noqa: RUF012

    def get_readonly_fields(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: Any | None = None,
    ) -> list[str] | tuple[Any, ...]:
        if obj:
            # Link id cannot be updated
            return (*self.readonly_fields, "templatelink_id")
        return self.readonly_fields
