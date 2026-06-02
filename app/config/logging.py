from enum import StrEnum


class Exporter(StrEnum):
    OTLP = "otlp"
    CONSOLE = "console"
