import environ

from .settings_base import *  # noqa: F403
from .settings_base import DEBUG, INSTALLED_APPS, MIDDLEWARE

env = environ.Env()

# Override debug if given by the env
if env.bool("DEBUG", None):
    DEBUG = env.bool("DEBUG")

if DEBUG:
    INSTALLED_APPS += ["django_extensions", "debug_toolbar"]

if DEBUG:
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware", *MIDDLEWARE]

# Allow to select as many items in the admin UI as needed, e.g. when batch-deleting nested objects
DATA_UPLOAD_MAX_NUMBER_FIELDS = None
