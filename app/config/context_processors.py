from typing import Any

from django.conf import settings
from django.http.request import HttpRequest

from config.version import APP_VERSION

# Header colors per environment: (background, text). The text color is chosen for sufficient
# contrast with the background.
APP_ENV_COLORS = {
    "local": ("#B5CCD2", "#1A1A1A"),  # swissgeo light blue
    "dev": ("#F3CB63", "#1A1A1A"),  # yellow
    "int": ("#E28054", "#1A1A1A"),  # swissgeo orange
    "prod": ("#D4311F", "#FFFFFF"),  # swissgeo red
}


def app_environment(request: HttpRequest) -> dict[str, Any]:
    """Provides the app environment and version, e.g. for the environment banner in the admin.

    For unknown environments, no colors are provided and the default admin colors are kept.
    """
    background, text = APP_ENV_COLORS.get(settings.APP_ENV, (None, None))
    return {
        "app_env": settings.APP_ENV,
        "app_version": APP_VERSION,
        "app_env_background": background,
        "app_env_text": text,
    }
