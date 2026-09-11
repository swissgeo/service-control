from django.contrib import admin

from .models import Concept, Thesaurus


@admin.register(Thesaurus)
class ThesaurusAdmin(admin.ModelAdmin):
    """Admin View for Thesaurus"""

    list_display = ("thesaurus_id",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Concept)
class ConceptAdmin(admin.ModelAdmin):
    """Admin View for Concept"""

    list_display = (
        "concept_id",
        "label_en",
        "thesaurus",
        "parent__label_en",
    )
    list_filter = ("thesaurus",)
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("concept_id", "label_en", "label_de")
