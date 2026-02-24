from typing import TYPE_CHECKING

from django.contrib import admin
from django.http import HttpRequest

from user.models import MachineUser, User

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http.request import HttpRequest


@admin.register(MachineUser)
class MachineUserAdmin(admin.ModelAdmin):
    """Admin View for machine users"""

    list_display = ("machine_user_id", "name", "organization", "created_by_user")

    def has_add_permission(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
    ) -> bool:
        # Disable creating machine users via admin UI as this will not create the app client
        return False

    def delete_queryset(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        queryset: QuerySet[MachineUser],
    ) -> None:
        for obj in queryset:
            obj.delete()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin View for users"""

    list_display = ("username", "created")
