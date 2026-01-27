from django.contrib import admin

from user.models import MachineUser


@admin.register(MachineUser)
class MachineUserAdmin(admin.ModelAdmin):  # type:ignore[type-arg]
    """Admin View for machine users"""

    list_display = ("machine_user_id", "name", "organization", "created_by_user")
