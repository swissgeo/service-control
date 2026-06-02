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


def _get_span_exporters() -> list[SpanExporter]:
    if settings.OTEL_SDK_DISABLED:
        return []

    span_exporters = []

    # OTLP exporter
    if settings.OTEL_ENABLE_OTLP_EXPORTER and Exporter.OTLP in settings.OTEL_TRACE_EXPORTERS:
        span_exporters.append(
            OTLPSpanExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                headers=settings.OTEL_EXPORTER_OTLP_HEADERS,
                insecure=settings.OTEL_EXPORTER_OTLP_INSECURE,
            )
        )

    # Console exporter
    if settings.OTEL_ENABLE_CONSOLE_EXPORTER and Exporter.CONSOLE in settings.OTEL_TRACE_EXPORTERS:
        span_exporters.append(ConsoleSpanExporter())

    return span_exporters


def _get_log_exporters() -> list[LogRecordExporter]:
    if settings.OTEL_SDK_DISABLED:
        return []

    log_exporters = []

    # OTLP exporter
    if settings.OTEL_ENABLE_OTLP_EXPORTER and Exporter.OTLP in settings.OTEL_LOGGING_EXPORTERS:
        log_exporters.append(
            OTLPLogExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                headers=settings.OTEL_EXPORTER_OTLP_HEADERS,
                insecure=settings.OTEL_EXPORTER_OTLP_INSECURE,
            )
        )

    # Console exporter
    if (
        settings.OTEL_ENABLE_CONSOLE_EXPORTER
        and Exporter.CONSOLE in settings.OTEL_LOGGING_EXPORTERS
    ):
        log_exporters.append(ConsoleLogRecordExporter())

    return log_exporters


def _get_metric_exporters() -> list[MetricExporter]:
    if settings.OTEL_SDK_DISABLED:
        return []

    metric_exporters = []

    # OTLP exporter
    if settings.OTEL_ENABLE_OTLP_EXPORTER and Exporter.OTLP in settings.OTEL_METRIC_EXPORTERS:
        metric_exporters.append(
            OTLPMetricExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                headers=settings.OTEL_EXPORTER_OTLP_HEADERS,
                insecure=settings.OTEL_EXPORTER_OTLP_INSECURE,
            )
        )

    # Console exporter
    if settings.OTEL_ENABLE_CONSOLE_EXPORTER and Exporter.CONSOLE in settings.OTEL_METRIC_EXPORTERS:
        metric_exporters.append(ConsoleMetricExporter())

    return metric_exporters


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


def _setup_metrics() -> MeterProvider | None:
    exporters = _get_metric_exporters()

    # The periodic exporter can be configured via environment variable:
    # OTEL_METRIC_EXPORT_INTERVAL [ms] => default to 60'000
    # OTEL_METRIC_EXPORT_TIMEOUT [ms] => default to 30'000
    metric_readers = [PeriodicExportingMetricReader(exporter) for exporter in exporters]

    meter_provider = MeterProvider(
        metric_readers=metric_readers,
        resource=_resource,
    )
    metrics.set_meter_provider(meter_provider)

    return meter_provider


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

    log_provider = LoggerProvider(resource=_resource)
    set_logger_provider(log_provider)
    log_exporters = _get_log_exporters()
    _setup_log_processors(log_provider, log_exporters)

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


def setup_trace_provider() -> None:
    """Setup OTEL trace provider.

    This is intentionally separated from initialization of instrumentation to support process forks
    as used by gunicorn. Each fork must setup the trace provider individually.
    """
    if settings.OTEL_SDK_DISABLED:
        return

    trace_provider = TracerProvider(resource=_resource)
    trace.set_tracer_provider(trace_provider)
    span_exporters = _get_span_exporters()
    _setup_span_processors(trace_provider, span_exporters)
    return


def initialize_metrics() -> bool:
    """Initialize OTEL metrics

    Setup OTEL metrics functionalities for third party libraries
    """
    if settings.OTEL_SDK_DISABLED:
        return False
    _setup_metrics()
    return True
