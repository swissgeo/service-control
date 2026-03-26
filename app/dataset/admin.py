from django.contrib import admin

from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """Admin View for Dataset"""

    list_display = ("dataset_id", "title_short_de")
    readonly_fields = ("created_at", "updated_at", "dataset_id")
    search_fields = ("dataset_id", "title_short_de")
