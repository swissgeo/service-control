import os

# for the oath2_proxy tests ENABLE_OAUTH2_PROXY needs to be set during test start up so that
# the middlewares and routes are loaded in settings_base, we set it here via os.environ because it
# is evaluated with the import of settings_dev
os.environ['ENABLE_OAUTH2_PROXY'] = 'True'

from .settings_dev import *  # pylint: disable=wildcard-import, unused-wildcard-import, wrong-import-position

TESTING = True
SECRET_KEY = 'django-insecure-6-72r#zx=sv6v@-4k@uf1gv32me@%yr*oqa*fu8&5l&a!ws)5#'  # nosec B105

os.environ["NINJA_SKIP_REGISTRY"] = "yes"
