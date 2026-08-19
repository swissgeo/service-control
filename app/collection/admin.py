from django.contrib import admin

from .models import Collection


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    """Admin View for Distribution"""

    list_display = ("collection_id", "title_de", "dataset", "data_source")
    readonly_fields = ("created_at", "updated_at")

    search_fields = (
        "collection_id",
        "dataset__dataset_id",
        "dataset__title_short_de",
    )
