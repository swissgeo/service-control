#!/usr/bin/env python
"""
WSGI config for project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

# ruff: noqa: E402 module-import-not-at-top-of-file

# isort:skip_file

# The gevent monkey import and patch suppress a warning, and a potential problem.
# Gunicorn would call it anyway, but if it tries to call it after the ssl module
# has been initialized in another module (like, in our code, by the botocore library),
# then it could lead to inconsistencies in how the ssl module is used. Thus we patch
# the ssl module through gevent.monkey.patch_all before any other import, especially
# the app import, which would cause the boto module to be loaded, which would in turn
# load the ssl module.
# NOTE: We do this only if wsgi.py is the main program, when running django runserver
# for local development, monkey patching creates the following error:
#     `RuntimeError: cannot release un-acquired lock`
from typing import Any

if __name__ == "__main__":
    import gevent.monkey

    gevent.monkey.patch_all()

# default to the setting that's being created in DOCKERFILE
from os import environ

environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Initialize OTEL.
# Initialize should be called as early as possible, but at least before the app is imported
# The order has a impact on how the libraries are instrumented. If called after app import,
# e.g. the django instrumentation has no effect.
from utils.otel import initialize_instrumentation, reinitialize_otel, shutdown_otel

import atexit

initialize_instrumentation()

from gunicorn.app.base import BaseApplication
from django.core.wsgi import get_wsgi_application
from gunicorn.arbiter import Arbiter
from gunicorn.workers.base import Worker
from gunicorn.config import Config
from django.core.handlers.wsgi import WSGIHandler

# Here we cannot use `from django.conf import settings` because it breaks the `make gunicornserve`
from config.settings_prod import get_logging_config

application = get_wsgi_application()


class StandaloneApplication(BaseApplication):
    cfg: Config

    def __init__(self, app: WSGIHandler, options: dict[str, Any]) -> None:
        self.options = options
        self.application = app
        super().__init__()

    def load_config(self) -> None:
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self) -> WSGIHandler:  # ty: ignore[invalid-method-override]
        return self.application


def post_fork(_server: Arbiter, _worker: Worker) -> None:
    # After forking, all background exporter threads (BatchSpanProcessor,
    # BatchLogRecordProcessor, PeriodicExportingMetricReader) are dead in the
    # worker process.
    reinitialize_otel()
    # Register shutdown in the worker process itself so spans, logs, and metrics
    # are flushed before the worker exits.
    atexit.register(shutdown_otel)


def on_exit(_server: Arbiter) -> None:
    # Flush and shut down the master process's own OTEL providers.
    shutdown_otel()


# We use the port 5000 as default, otherwise we set the HTTP_PORT env variable within the container.
if __name__ == "__main__":
    HTTP_PORT = str(environ.get("HTTP_PORT", "8000"))

    # Get TLS configuration
    keyfile = environ.get("GUNICORN_KEYFILE")
    certfile = environ.get("GUNICORN_CERTFILE")

    # Bind to 0.0.0.0 to let your app listen to all network interfaces.
    options = {
        "bind": f"{'0.0.0.0'}:{HTTP_PORT}",  # noqa: S104
        "worker_class": "gevent",
        "workers": int(
            environ.get("GUNICORN_WORKERS", "2")
        ),  # scaling horizontally is left to Kubernetes
        "worker_tmp_dir": environ.get("GUNICORN_WORKER_TMP_DIR", None),
        "keepalive": int(environ.get("GUNICORN_KEEPALIVE", "2")),
        "timeout": 60,
        "logconfig_dict": get_logging_config(),
        "post_fork": post_fork,
        "on_exit": on_exit,
    }

    if keyfile and certfile:
        options["keyfile"] = keyfile
        options["certfile"] = certfile
    elif keyfile or certfile:
        raise RuntimeError("Both GUNICORN_KEYFILE and GUNICORN_CERTFILE must be set for TLS")

    StandaloneApplication(application, options).run()
