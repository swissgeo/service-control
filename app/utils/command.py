import logging
import uuid
from traceback import format_exception
from typing import Any, TextIO

from opentelemetry import metrics, trace

from django.core.management.base import BaseCommand, CommandParser


class CustomBaseCommand(BaseCommand):
    """
    A custom Django management command that adds proper support for logging.

    Example how to subclass:

        class MyCommand(CustomBaseCommand):

            def add_arguments(self, parser: CommandParser) -> None:
                super().add_arguments(parser)
                parser.add_argument('--flag', action='store_true')

            def handle(self, *args: Any, **options: dict['str', Any]) -> None:
                if options['flag']:  # or self.options['flag']
                    self.print('flag was set')
                self.print_success('done')

    """

    def __init__(
        self,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
        no_color: bool = False,
        force_color: bool = False,
    ) -> None:
        super().__init__(stdout, stderr, no_color, force_color)
        self.logger = logging.getLogger(self.__module__)
        self.options: dict[str, Any] = {}

    def add_arguments(self, parser: CommandParser) -> None:
        """
        Entry point for add custom arguments. Options will also be available as self.options during
        handle.

        Subclasses may want to extend this method.
        """

        parser.add_argument("--logger", action="store_true", help="use logger configuration")

    def handle(self, *args: Any, **options: dict[str, Any]) -> None:
        """
        The actual logic of the command.

        Subclasses must implement this method.
        """

        raise NotImplementedError("subclasses of CustomBaseCommand must provide a handle() method")

    def execute(self, *args: Any, **options: dict[str, Any]) -> None:
        """Try to execute the command and log any exceptions if the logger is configured."""

        self.options = options
        if self.options["logger"]:
            try:
                super().execute(*args, **options)
            except Exception as e:  # noqa: BLE001
                self.print_error(e, exc_info=True)
        else:
            super().execute(*args, **options)

    def print(self, message: str, *args: Any, level: int = 2, **kwargs: Any) -> None:
        if self.options["verbosity"] >= level:
            if self.options["logger"]:
                self.logger.info(message, *args, **kwargs)
            else:
                if len(kwargs) > 0:
                    message = (
                        message + " " + ", ".join(f"{key}={value}" for key, value in kwargs.items())
                    )
                self.stdout.write(message % args if args else message)

    def print_warning(self, message: str, *args: Any, level: int = 1, **kwargs: Any) -> None:
        if self.options["verbosity"] >= level:
            if self.options["logger"]:
                self.logger.warning(message, *args, **kwargs)
            else:
                if len(kwargs) > 0:
                    message = (
                        message + " " + ", ".join(f"{key}={value}" for key, value in kwargs.items())
                    )
                self.stdout.write(self.style.WARNING(message % (args)))

    def print_success(self, message: str, *args: Any, level: int = 1, **kwargs: Any) -> None:
        if self.options["verbosity"] >= level:
            if self.options["logger"]:
                self.logger.info(message, *args, **kwargs)
            else:
                if len(kwargs) > 0:
                    message = (
                        message + " " + ", ".join(f"{key}={value}" for key, value in kwargs.items())
                    )
                self.stdout.write(self.style.SUCCESS(message % (args)))

    def print_error(self, message: str | Exception, *args: Any, **kwargs: Any) -> None:
        if self.options["logger"]:
            self.logger.error(message, *args, **kwargs)
        else:
            if isinstance(message, Exception):
                message = "".join(format_exception(message))
            else:
                message = str(message)
            if len(kwargs) > 0:
                message = (
                    message + "\n" + ", ".join(f"{key}={value}" for key, value in kwargs.items())
                )
            self.stderr.write(self.style.ERROR(message % (args)))

    def write_command_metrics(self, log_metrics: dict[str, int]) -> None:
        """Emit OTel metrics from a metrics dict.

        For each key (used as the metrics name), integer values are emitted as
        individual gauges. job_id is added as an attribute to each gauge.
        """
        # job_id is used as a common attribute in metrics to link different metrics related to the
        # same import run. Use the OTel trace ID if available, otherwise fall back to a UUID.
        span_ctx = trace.get_current_span().get_span_context()
        job_id = format(span_ctx.trace_id, "032x") if span_ctx.is_valid else str(uuid.uuid4())
        meter = metrics.get_meter(__name__)
        for counter_name, value in log_metrics.items():
            meter.create_gauge(f"{self._metrics_prefix()}{counter_name}").set(
                value, {"job_id": job_id}
            )

    def _metrics_prefix(self) -> str:
        """Return a prefix for metrics emitted by this command, based on the module name."""
        return f"swissgeo.service_control.{self.__module__.split('.')[-1]}."
