from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html_join

from legal.models import GeopoliticalEntity


@admin.register(GeopoliticalEntity)
class GeopoliticalEntityAdmin(admin.ModelAdmin):
    """Admin View for Geopolicitcal Entity"""

    list_display = ("geopolitical_entity_id", "type", "name", "child_list")

    @admin.display(description="child entities")
    def child_list(self, obj: GeopoliticalEntity) -> str:
        return format_html_join(
            "\n",
            '<a href="{}">{}</a><br>',
            (
                (
                    reverse("admin:legal_geopoliticalentity_change", args=[child.pk]),
                    str(child),
                )
                for child in obj.children.all()  # ty: ignore[unresolved-attribute]
            ),
        )
