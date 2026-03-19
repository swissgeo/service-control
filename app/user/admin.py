from typing import TYPE_CHECKING, ClassVar

from django.contrib import admin
from django.contrib.auth.models import Group
from django.forms import ModelForm, MultipleChoiceField, SelectMultiple
from django.http import HttpRequest

from config.authorization import VPRole
from user.models import CustomUser

if TYPE_CHECKING:
    from django.http.request import HttpRequest


class CustomUserAdminForm(ModelForm):
    roles = MultipleChoiceField(
        choices=VPRole.choices(),
        required=False,
        widget=SelectMultiple,
    )

    class Meta:
        model = CustomUser
        fields: ClassVar[list[str]] = [
            "user_type",
            "sub",
            "cognito_username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
            "organization",
            "roles",
            "created_by_user",
            "vp_machine_user_policy_id",
            "last_login",
            "date_joined",
        ]


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    """Admin View for Users"""

    list_display = (
        "sub",
        "cognito_username",
        "email",
        "first_name",
        "last_name",
        "organization",
        "user_type",
        "is_staff",
        "is_active",
    )

    form = CustomUserAdminForm

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


admin.site.unregister(Group)
