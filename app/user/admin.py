from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import Group
from django.forms import ModelChoiceField, ModelForm, MultipleChoiceField, SelectMultiple

from config.authorization import VPRole
from organization.models import Unit
from user.models import HumanUser, MachineUser

if TYPE_CHECKING:
    from django.http import HttpRequest


class OrganizationScopedUnitForm(ModelForm):
    """
    Custom form to limit the unit choices to the units of the selected organization in the admin UI.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        unit_field = self.fields.get("unit")
        if not isinstance(unit_field, ModelChoiceField):
            return

        organization_pk = self.data.get(self.add_prefix("organization"))
        if organization_pk:
            unit_field.queryset = Unit.objects.filter(organization_id=organization_pk)
            return

        if self.instance and self.instance.organization_id:
            unit_field.queryset = Unit.objects.filter(organization_id=self.instance.organization_id)
            return

        unit_field.queryset = Unit.objects.none()


class HumanUserAdminForm(OrganizationScopedUnitForm):
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
            "unit",
            "roles",
            "is_staff",
            "is_superuser",
            "is_active",
            "last_login",
            "date_joined",
        ]
        help_texts: ClassVar[dict[str, str]] = {
            "sub": "Cognito user sub.",
            "is_superuser": (
                "Designates that this user has all permissions without explicitly "
                "assigning them. This is set based on the user being in the group "
                f"{settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS}"
            ),
            "is_staff": (
                "Designates that this user can log into this admin site. This is "
                "set based on the user being in the group "
                f"{settings.OAUTH2_PROXY_DJANGO_ADMIN_GROUPS}"
            ),
        }


class MachineUserAdminForm(OrganizationScopedUnitForm):
    class Meta:
        model = MachineUser
        fields: ClassVar[list[str]] = [
            "sub",
            "name",
            "organization",
            "unit",
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
        "unit",
        "is_active",
        "is_superuser",
    )
    readonly_fields = (
        "sub",
        "cognito_username",
        "date_joined",
        "last_login",
        "is_superuser",
        "is_staff",
    )

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
        "unit",
        "created_by_user",
        "is_active",
        "is_superuser",
    )
    readonly_fields = ("vp_machine_user_policy_id", "date_joined")


admin.site.unregister(Group)
