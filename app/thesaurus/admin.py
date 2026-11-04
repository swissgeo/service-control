from django.contrib import admin

from utils.admin import HideFieldsetsOnAddMixin

from .models import Concept, Thesaurus


@admin.register(Thesaurus)
class ThesaurusAdmin(HideFieldsetsOnAddMixin, admin.ModelAdmin):
    """Admin View for Thesaurus"""

    list_display = ("thesaurus_id",)
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("thesaurus_id",)
    fieldsets = (
        ("Identification", {"fields": ("thesaurus_id",)}),
        ("Metadata", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )


@admin.register(Concept)
class ConceptAdmin(HideFieldsetsOnAddMixin, admin.ModelAdmin):
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
    save_on_top = True
    fieldsets = (
        (
            "Identification",
            {"fields": (("thesaurus", "concept_id"), ("parent", "order"))},
        ),
        ("Labels", {"fields": ("label_de", "label_fr", "label_en", "label_it", "label_rm")}),
        ("Metadata", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )
