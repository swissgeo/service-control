from django.apps import AppConfig
from django.db.models.signals import m2m_changed


class UserConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "user"

    def ready(self) -> None:
        from user.models import CustomUser  # noqa: PLC0415
        from user.signals import sync_custom_user_roles_to_cognito  # noqa: PLC0415

        m2m_changed.connect(
            receiver=sync_custom_user_roles_to_cognito, sender=CustomUser.roles.through
        )
