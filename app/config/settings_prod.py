from .settings_base import BASE_DIR
from .settings_base import *  # noqa: F403

DEBUG = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_ROOT = BASE_DIR / 'var' / 'www' / 'service_control' / 'static_files'
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
