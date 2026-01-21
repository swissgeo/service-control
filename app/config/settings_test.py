import os

# for tests, we want to always use the the postgres superuser from the docker container in order to
# be able to create new test databases
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PW'] = 'postgres'

from .settings_dev import * # noqa: F401, F403

TESTING = True
SECRET_KEY = 'django-insecure-6-72r#zx=sv6v@-4k@uf1gv32me@%yr*oqa*fu8&5l&a!ws)5#'  # nosec B105

os.environ["NINJA_SKIP_REGISTRY"] = "yes"
