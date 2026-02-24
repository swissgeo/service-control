from typing import TYPE_CHECKING, ClassVar

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpRequest

from user.models import CustomUser, MachineUser

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


class CustomUserInline(admin.StackedInline):
    model = CustomUser
    can_delete = False


class UserAdmin(BaseUserAdmin):
    inlines: ClassVar[list[type[CustomUserInline]]] = [CustomUserInline]

    list_display = ("username", "email", "first_name", "last_name", "get_organization", "is_staff")

    @admin.display(description="Organization")
    def get_organization(self, obj: User) -> str:
        """Display the organization from the related CustomUser"""
        return obj.customuser.organization  # ty: ignore[unresolved-attribute]


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
