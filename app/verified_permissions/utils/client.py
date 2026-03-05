from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

from verified_permissions.utils.local import Client as LocalClient
from verified_permissions.utils.verified_permissions import Client as VerifiedPermissionsClient

if TYPE_CHECKING:
    from verified_permissions.utils.base import BaseClient

Client: type[BaseClient] = (
    LocalClient if settings.USE_LOCAL_VERIFIED_PERMISSIONS else VerifiedPermissionsClient
)
