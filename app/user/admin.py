from typing import TYPE_CHECKING

from asgiref.sync import async_to_sync

from django.contrib import admin

from user.models import MachineUser, User

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.forms import ModelForm
    from django.http.request import HttpRequest


@admin.register(MachineUser)
class MachineUserAdmin(admin.ModelAdmin):
    """Admin View for machine users"""

    list_display = ("machine_user_id", "name", "organization", "created_by_user")

    def save_model(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: MachineUser,
        form: ModelForm[MachineUser],  # noqa: ARG002 unused argument
        change: bool,  # noqa: ARG002 unused argument
    ) -> None:
        async_to_sync(obj.save_and_sync)()

    def delete_model(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        obj: MachineUser,
    ) -> None:
        async_to_sync(obj.delete_and_sync)()

    def delete_queryset(
        self,
        request: HttpRequest,  # noqa: ARG002 unused argument
        queryset: QuerySet[MachineUser],
    ) -> None:
        for obj in queryset:
            async_to_sync(obj.delete_and_sync)()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin View for users"""

    list_display = ("username", "created")
