from django.apps import AppConfig
from django.db.models.signals import post_delete


class UserConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "user"

    def ready(self) -> None:
        from user.models import MachineUser  # noqa: PLC0415
        from user.signals import machine_user_post_delete  # noqa: PLC0415

        post_delete.connect(receiver=machine_user_post_delete, sender=MachineUser)
