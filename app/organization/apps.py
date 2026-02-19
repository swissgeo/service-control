from django.apps import AppConfig
from django.db.models.signals import post_delete, post_save


class OrganizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "organization"

    def ready(self) -> None:
        from organization.models import Organization, Unit  # noqa: PLC0415
        from organization.signals import (  # noqa: PLC0415
            organization_post_delete,
            organization_post_save,
            unit_post_delete,
            unit_post_save,
        )

        post_save.connect(receiver=organization_post_save, sender=Organization)
        post_delete.connect(receiver=organization_post_delete, sender=Organization)
        post_save.connect(receiver=unit_post_save, sender=Unit)
        post_delete.connect(receiver=unit_post_delete, sender=Unit)
