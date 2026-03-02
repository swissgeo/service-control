from typing import TYPE_CHECKING, ClassVar

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpRequest

from user.models import CustomUser

if TYPE_CHECKING:
    from django.http.request import HttpRequest


class CustomUserInline(admin.StackedInline):
    model = CustomUser
    can_delete = False


class UserAdmin(BaseUserAdmin):
    inlines: ClassVar[list[type[CustomUserInline]]] = [CustomUserInline]

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "get_organization",
        "get_user_type",
        "is_staff",
        "is_active",
    )

    @admin.display(description="Organization")
    def get_organization(self, obj: User) -> str:
        """Display the organization from the related CustomUser"""
        return obj.customuser.organization  # ty: ignore[unresolved-attribute]

    @admin.display(description="Type")
    def get_user_type(self, obj: User) -> str:
        """Display the user type from the related CustomUser"""
        return obj.customuser.user_type  # ty: ignore[unresolved-attribute]

    def has_add_permission(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
    ) -> bool:
        # Disable creating human users via admin UI, cognito is the source of users.
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argumentrequest
        obj: CustomUser | None = None,  # noqa: ARG002 unused argumentrequest
    ) -> bool:
        # Disable deleting users, cognito is the source of users. If necessary, users can be
        # disabled.
        return False


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
