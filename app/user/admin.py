from django.contrib import admin

from user.models import MachineUser, User


@admin.register(MachineUser)
class MachineUserAdmin(admin.ModelAdmin):  # type:ignore[type-arg]
    """Admin View for machine users"""

    list_display = ("machine_user_id", "name", "organization", "created_by_user")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):  # type:ignore[type-arg]
    """Admin View for users"""

    list_display = ("username", "created")
