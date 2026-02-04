from os import getenv
from typing import Any, Protocol

Scope = dict[str, Any]


class AsgiApplication(Protocol):
    async def __call__(
        self,
        scope: Scope,
        receive: Any,
        send: Any,
    ) -> None: ...


def strtobool(value: str) -> bool:
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    value = value.lower()
    if value in ("y", "yes", "t", "true", "on", "1"):
        return True
    if value in ("n", "no", "f", "false", "off", "0"):
        return False
    raise ValueError(f"invalid truth value '{value}'")  # noqa: TRY003


def tracing_enabled() -> bool:
    return not strtobool(getenv("OTEL_SDK_DISABLED", "false"))


def initialize_tracing(application: AsgiApplication | None = None) -> AsgiApplication | None:
    if tracing_enabled():
        # Since we created a new tracer, the default span processor is gone. We need to
        # create a new one using the default OTEL env variables and ad it to the tracer.
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: PLC0415
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource  # noqa: PLC0415
        from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: PLC0415
        from opentelemetry.trace import set_tracer_provider  # noqa: PLC0415

        span_processor = BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
                headers=getenv("OTEL_EXPORTER_OTLP_HEADERS"),
                insecure=strtobool(getenv("OTEL_EXPORTER_OTLP_INSECURE", "false")),
            ),
        )
        provider = TracerProvider(resource=Resource.create())
        provider.add_span_processor(span_processor)
        set_tracer_provider(provider)

        if strtobool(getenv("OTEL_ENABLE_DJANGO", "false")) and application:
            from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware  # noqa: PLC0415

            application = OpenTelemetryMiddleware(application)

        if strtobool(getenv("OTEL_ENABLE_BOTO", "false")):
            from opentelemetry.instrumentation.aiobotocore import (  # noqa: PLC0415
                AioBotocoreInstrumentor,
            )
            from opentelemetry.instrumentation.botocore import BotocoreInstrumentor  # noqa: PLC0415

            BotocoreInstrumentor().instrument()
            AioBotocoreInstrumentor().instrument()

        if strtobool(getenv("OTEL_ENABLE_PSYCOPG", "false")):
            from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor  # noqa: PLC0415

            PsycopgInstrumentor().instrument()

        if strtobool(getenv("OTEL_ENABLE_LOGGING", "false")):
            from opentelemetry.instrumentation.logging import LoggingInstrumentor  # noqa: PLC0415

            LoggingInstrumentor().instrument()

    return application
