from polymorphic.admin import (
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
    PolymorphicParentModelAdmin,
)

from django.contrib import admin

from .models import Distribution, ExternalWMSDistribution, ExternalWMTSDistribution


@admin.register(Distribution)
class DistributionAdmin(PolymorphicParentModelAdmin):
    """Admin View for Distribution"""

    base_model = Distribution  # Optional, explicitly set here.
    child_models = (ExternalWMSDistribution, ExternalWMTSDistribution)

    list_display = ("distribution_id", "title")
    readonly_fields = ("created_at", "updated_at")
    list_filter = (PolymorphicChildModelFilter,)  # This is optional.


@admin.register(ExternalWMTSDistribution)
class ExternalWMTSDistributionAdmin(PolymorphicChildModelAdmin):
    """Admin View for ExternalWMTSDistribution"""

    list_display = ("distribution_id", "title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ExternalWMSDistribution)
class ExternalWMSDistributionAdmin(PolymorphicChildModelAdmin):
    """Admin View for ExternalWMSDistribution"""

    list_display = ("distribution_id", "title")
    readonly_fields = ("created_at", "updated_at")
