from typing import TYPE_CHECKING, ClassVar

from django.contrib import admin
from django.contrib.auth.models import Group
from django.forms import ModelForm, MultipleChoiceField, SelectMultiple

from config.authorization import VPRole
from user.models import HumanUser, MachineUser

if TYPE_CHECKING:
    from django.http import HttpRequest


class HumanUserAdminForm(ModelForm):
    roles = MultipleChoiceField(choices=VPRole.choices(), required=False, widget=SelectMultiple)

    class Meta:
        model = HumanUser
        fields: ClassVar[list[str]] = [
            "sub",
            "cognito_username",
            "email",
            "first_name",
            "last_name",
            "organization",
            "roles",
            "is_staff",
            "is_superuser",
            "is_active",
            "last_login",
            "date_joined",
        ]
        help_texts: ClassVar[dict[str, str]] = {
            "sub": "Cognito user sub.",
        }


class MachineUserAdminForm(ModelForm):
    roles = MultipleChoiceField(choices=VPRole.choices(), required=False, widget=SelectMultiple)

    class Meta:
        model = MachineUser
        fields: ClassVar[list[str]] = [
            "sub",
            "name",
            "organization",
            "is_staff",
            "is_superuser",
            "created_by_user",
            "vp_machine_user_policy_id",
            "is_active",
            "date_joined",
        ]
        help_texts: ClassVar[dict[str, str]] = {
            "sub": "Create app client in cognito first and provide the app client ID here.",
        }


@admin.register(HumanUser)
class HumanUserAdmin(admin.ModelAdmin):
    form = HumanUserAdminForm
    list_display = (
        "sub",
        "cognito_username",
        "email",
        "first_name",
        "last_name",
        "organization",
        "is_active",
        "is_superuser",
    )
    readonly_fields = ("sub", "cognito_username", "date_joined", "last_login")

    def has_add_permission(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
    ) -> bool:
        # Disable creating human users via admin UI, cognito is the source of users.
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argumentrequest
        obj: HumanUser | None = None,  # noqa: ARG002 unused argumentrequest
    ) -> bool:
        # Disable deleting users, cognito is the source of users. If necessary, users can be
        # disabled.
        return False


@admin.register(MachineUser)
class MachineUserAdmin(admin.ModelAdmin):
    form = MachineUserAdminForm
    list_display = (
        "sub",
        "name",
        "organization",
        "created_by_user",
        "is_active",
        "is_superuser",
    )
    readonly_fields = ("vp_machine_user_policy_id", "date_joined")


admin.site.unregister(Group)
