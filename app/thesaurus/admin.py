from django.contrib import admin

from .models import Keyword, Thesaurus


@admin.register(Thesaurus)
class ThesaurusAdmin(admin.ModelAdmin):
    """Admin View for Thesaurus"""

    list_display = ("thesaurus_id",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    """Admin View for Keyword"""

    list_display = ("keyword_id", "label_en", "thesaurus")
    list_filter = ("thesaurus",)
    readonly_fields = ("created_at", "updated_at")
