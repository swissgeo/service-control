from django.contrib import admin

from .models import Distribution, ExternalWMSDistribution, ExternalWMTSDistribution


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    """Admin View for Distribution"""

    list_display = ("distribution_id", "title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ExternalWMTSDistribution)
class ExternalWMTSDistributionAdmin(admin.ModelAdmin):
    """Admin View for ExternalWMTSDistribution"""

    list_display = ("distribution_id", "title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ExternalWMSDistribution)
class ExternalWMSDistributionAdmin(admin.ModelAdmin):
    """Admin View for ExternalWMSDistribution"""

    list_display = ("distribution_id", "title")
    readonly_fields = ("created_at", "updated_at")
