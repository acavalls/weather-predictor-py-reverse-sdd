"""Logging adapter — wraps Python stdlib logging behind Logger port."""

from __future__ import annotations

import logging

from src.domain.shared.logger import Logger


class LoggingAdapter(Logger):
    """Adapter that delegates to Python's standard logging module.

    Args:
        name: Logger name (typically __name__ of the calling module).
        level: Minimum log level (default: INFO).
    """

    def __init__(self, name: str, level: int = logging.INFO) -> None:
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

    def info(self, msg: str, *args: object) -> None:
        self._logger.info(msg, *args)

    def warning(self, msg: str, *args: object) -> None:
        self._logger.warning(msg, *args)

    def error(self, msg: str, *args: object) -> None:
        self._logger.error(msg, *args)

    def exception(self, msg: str, *args: object) -> None:
        self._logger.exception(msg, *args)

    def debug(self, msg: str, *args: object) -> None:
        self._logger.debug(msg, *args)


class NullLogger(Logger):
    """No-op logger for tests and defaults. Silently discards all messages."""

    def info(self, msg: str, *args: object) -> None:
        pass

    def warning(self, msg: str, *args: object) -> None:
        pass

    def error(self, msg: str, *args: object) -> None:
        pass

    def exception(self, msg: str, *args: object) -> None:
        pass

    def debug(self, msg: str, *args: object) -> None:
        pass
