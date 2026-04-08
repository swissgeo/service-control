from django.contrib import admin

from .models import Dataset, DatasetContact


class DatasetContactInline(admin.TabularInline):
    model = DatasetContact
    extra = 0


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """Admin View for Dataset"""

    list_display = ("dataset_id", "title_short_de")
    # TODO: depending on how we handle identefiers, we might want to make dataset_id read only in
    # edit or implement auto-generation for identifiers (probably preferrable)
    readonly_fields = ("created_at", "updated_at", "dataset_id")
    search_fields = ("dataset_id", "title_short_de")
    filter_horizontal = ("keywords",)
    inlines = (DatasetContactInline,)
