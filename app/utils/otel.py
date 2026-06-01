import logging

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    ConsoleLogRecordExporter,
    LogRecordExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    MetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter

from django.conf import settings

from config.logging import Exporter

_resource = Resource.create({"service.name": "service-control"})


def _get_providers() -> tuple[LoggerProvider | None, TracerProvider | None]:
    if settings.OTEL_SDK_DISABLED:
        return None, None
    # Log provider can be used together with logging instrumentation to send logs to the OTEL
    # configured exporter in the correct OTEL format
    log_provider = LoggerProvider(resource=_resource)
    set_logger_provider(log_provider)

    # Trace provider
    trace_provider = TracerProvider(resource=_resource)
    trace.set_tracer_provider(trace_provider)

    return log_provider, trace_provider


def _get_exporters() -> tuple[
    list[LogRecordExporter],
    list[SpanExporter],
    list[MetricExporter],
]:
    if settings.OTEL_SDK_DISABLED:
        return [], [], []

    metric_exporters = []
    span_exporters = []
    log_exporters = []

    # OTLP exporters
    if settings.OTEL_ENABLE_OTLP_EXPORTER:
        # Tracing OTLP exporter
        if Exporter.OTLP in settings.OTEL_TRACE_EXPORTERS:
            span_exporters.append(
                OTLPSpanExporter(
                    endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                    headers=settings.OTEL_EXPORTER_OTLP_HEADERS,
                    insecure=settings.OTEL_EXPORTER_OTLP_INSECURE,
                )
            )
        # Metrics OTLP exporter
        if Exporter.OTLP in settings.OTEL_METRIC_EXPORTERS:
            metric_exporters.append(
                OTLPMetricExporter(
                    endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                    headers=settings.OTEL_EXPORTER_OTLP_HEADERS,
                    insecure=settings.OTEL_EXPORTER_OTLP_INSECURE,
                )
            )
        # Logs OTLP exporter
        if Exporter.OTLP in settings.OTEL_LOGGING_EXPORTERS:
            log_exporters.append(
                OTLPLogExporter(
                    endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                    headers=settings.OTEL_EXPORTER_OTLP_HEADERS,
                    insecure=settings.OTEL_EXPORTER_OTLP_INSECURE,
                )
            )

    # Console exporters
    if settings.OTEL_ENABLE_CONSOLE_EXPORTER:
        if Exporter.CONSOLE in settings.OTEL_TRACE_EXPORTERS:
            span_exporters.append(ConsoleSpanExporter())
        if Exporter.CONSOLE in settings.OTEL_METRIC_EXPORTERS:
            metric_exporters.append(ConsoleMetricExporter())
        if Exporter.CONSOLE in settings.OTEL_LOGGING_EXPORTERS:
            log_exporters.append(ConsoleLogRecordExporter())

    return log_exporters, span_exporters, metric_exporters


def _setup_log_processors(
    provider: LoggerProvider | None,
    exporters: list[LogRecordExporter],
) -> None:
    if provider is None:
        return

    for exporter in exporters:
        provider.add_log_record_processor(BatchLogRecordProcessor(exporter))


def _setup_span_processors(
    provider: TracerProvider | None,
    exporters: list[SpanExporter],
) -> None:
    if provider is None:
        return

    for exporter in exporters:
        provider.add_span_processor(BatchSpanProcessor(exporter))


def _setup_metrics(exporters: list[MetricExporter]) -> MeterProvider | None:
    if settings.OTEL_SDK_DISABLED or not settings.OTEL_ENABLE_METRICS:
        return None

    metrics_readers = [
        PeriodicExportingMetricReader(
            exporter=exporter,
            export_interval_millis=settings.OTEL_METRIC_EXPORT_INTERVAL_MS,
            export_timeout_millis=settings.OTEL_METRIC_EXPORT_TIMEOUT_MS,
        )
        for exporter in exporters
    ]
    meter_provider = MeterProvider(metric_readers=metrics_readers, resource=_resource)
    metrics.set_meter_provider(meter_provider)
    return meter_provider


# ------------------------------------------------------------------------------
# NOTE: Import-time setup is intentional.
#
# This allows gunicorn's logging.dictConfig() to resolve:
#
#   handlers:
#     otel:
#       (): app.otel.get_otel_handler
#
# At that point, get_otel_handler() must be importable and must already have access
# to an initialized LoggerProvider.

log_provider, trace_provider = _get_providers()

log_exporters, span_exporters, metric_exporters = _get_exporters()

_setup_log_processors(log_provider, log_exporters)
_setup_span_processors(trace_provider, span_exporters)

meter_provider = _setup_metrics(metric_exporters)


def _update_otel_logging_handlers(new_log_provider: LoggerProvider) -> None:
    """Update all LoggingHandler instances in Python's logging system to use the new provider.

    After a process fork, LoggingHandler instances inherited from the parent hold a reference
    to the old LoggerProvider with dead background threads. This patches them in-place to point
    to the newly-created provider so log records are actually exported.
    """

    def _patch(handler: logging.Handler) -> None:
        if isinstance(handler, LoggingHandler):
            handler._logger_provider = new_log_provider  # noqa: SLF001

    for handler in logging.root.handlers:
        _patch(handler)

    for logger_or_placeholder in logging.root.manager.loggerDict.values():
        if isinstance(logger_or_placeholder, logging.Logger):
            for handler in logger_or_placeholder.handlers:
                _patch(handler)


def reinitialize_otel() -> None:
    """Reinitialize OTEL providers after a process fork (e.g. Gunicorn post_fork).

    After forking, all background threads used by BatchSpanProcessor,
    BatchLogRecordProcessor, and PeriodicExportingMetricReader are dead in the
    child process. This function creates fresh ones with new background threads.
    """
    global log_provider, trace_provider, meter_provider  # noqa: PLW0603

    new_log_provider, new_trace_provider = _get_providers()
    new_log_exporters, new_span_exporters, new_metric_exporters = _get_exporters()

    _setup_log_processors(new_log_provider, new_log_exporters)
    _setup_span_processors(new_trace_provider, new_span_exporters)
    new_meter_provider = _setup_metrics(new_metric_exporters)

    log_provider = new_log_provider
    trace_provider = new_trace_provider
    meter_provider = new_meter_provider

    # Patch existing LoggingHandler instances so they emit to the new provider.
    if new_log_provider is not None:
        _update_otel_logging_handlers(new_log_provider)


def get_otel_handler() -> logging.Handler:
    """Get the OTEL handler for logging

    This will return a handler that can be used to send logs to OTEL. The handler will be configured
    based on the OTEL settings.

    Returns:
        logging.Handler: OTEL handler for logging
    """

    if settings.OTEL_SDK_DISABLED:
        raise ValueError(
            "Cannot use OTEL handler in logging configuration when OTEL_SDK_DISABLED is true"
        )
    if log_provider is None:
        raise ValueError("OTEL LoggerProvider is not initialized")

    return LoggingHandler(logger_provider=log_provider)


def initialize_instrumentation() -> bool:
    """Initialize OTEL instrumentation

    Setup OTEL tracing functionalities for third party libraries
    """
    if settings.OTEL_SDK_DISABLED:
        return False

    if settings.OTEL_ENABLE_DJANGO and not DjangoInstrumentor().is_instrumented_by_opentelemetry:
        DjangoInstrumentor().instrument()
    if settings.OTEL_ENABLE_BOTO and not BotocoreInstrumentor().is_instrumented_by_opentelemetry:
        BotocoreInstrumentor().instrument()
    if settings.OTEL_ENABLE_PSYCOPG and not PsycopgInstrumentor().is_instrumented_by_opentelemetry:
        PsycopgInstrumentor().instrument()

    return True


def shutdown_otel() -> None:
    """Flush and shutdown OTEL providers/processors on application shutdown."""

    if trace_provider is not None:
        trace_provider.shutdown()

    if log_provider is not None:
        log_provider.shutdown()

    if meter_provider is not None:
        meter_provider.shutdown()
