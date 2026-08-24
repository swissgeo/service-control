#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys

from opentelemetry import trace

from utils.logging import redirect_std_to_logger


def main() -> None:
    """Run administrative tasks."""
    # default to the setting that's being created in DOCKERFILE
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    # otel.py accesses Django settings at module level, so it must be imported
    # only after DJANGO_SETTINGS_MODULE has been set.
    from utils.otel import (  # noqa: PLC0415
        initialize_instrumentation,
        initialize_metrics,
        setup_trace_provider,
    )

    try:
        from django.core.management import execute_from_command_line  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?",
        ) from exc

    tracing_enabled = initialize_instrumentation()
    initialize_metrics()
    if tracing_enabled:
        setup_trace_provider()
        name = sys.argv[1] if len(sys.argv) > 1 else sys.argv[0]
        tracer = trace.get_tracer(name)
        with tracer.start_as_current_span(name=name):
            execute_from_command_line(sys.argv)
    else:
        execute_from_command_line(sys.argv)


if __name__ == "__main__":
    if "--redirect-std-to-logger" in sys.argv:
        sys.argv.remove("--redirect-std-to-logger")
        with redirect_std_to_logger(__name__):
            main()
    else:
        main()
