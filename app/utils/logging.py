from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from logging import ERROR, INFO, getLogger
from logging.config import dictConfig
from logging.handlers import QueueListener
from time import time
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from collections.abc import Generator
    from queue import Queue


class TimestampedStringIO(StringIO):
    """A StringIO-like in-memory text buffer that logs each write and stores a timestamp for when
    the content was appended.

    """

    def __init__(self, level: int) -> None:
        super().__init__()
        self.level = level
        self.messages: list[tuple[float, int, str]] = []

    def write(self, s: str) -> int:
        message = s.strip()
        if message:
            self.messages.append((time(), self.level, message))
        return len(s)


@contextmanager
def redirect_std_to_logger(
    logger_name: str, stderr_level: int = ERROR, stdout_level: int = INFO
) -> Generator[None]:
    """A context manager that redirects sys.stdout and sys.stderr to the logger using the given
    levels.

    Use it like this:

        import sys
        from utils.logging import redirect_std_to_logger

        with redirect_std_to_logger('my_module'):
            sys.out('This gets logged with level INFO')
            sys.err('This gets logged with level ERROR')

    """

    stderr = TimestampedStringIO(stderr_level)
    stdout = TimestampedStringIO(stdout_level)
    exception: Exception | None = None
    with redirect_stderr(stderr), redirect_stdout(stdout):
        try:
            yield
        except Exception as e:  # noqa: BLE001
            exception = e

    logger = getLogger(logger_name)
    dictConfig(settings.LOGGING)
    for _, level, message in sorted(stderr.messages + stdout.messages):
        logger.log(level, message)
    if exception:
        logger.exception(exception)


class AutoStartQueueListener(QueueListener):
    """
    A queue listener which automatically starts when created.

    Use this handler in conjunction with a queue handler before your existing handlers:

        handlers:
        existing_handler:
            ...
        queue_listener:
            class: logging.handlers.QueueHandler
            listener: utils.logging.AutoStartQueueListener
            queue:
            (): queue.Queue
            maxsize: 1000
            handlers:
            - existing_handler

    """

    def __init__(self, queue: Queue, *handlers, respect_handler_level: bool = False) -> None:
        super().__init__(queue, *handlers, respect_handler_level=respect_handler_level)
        self.start()
