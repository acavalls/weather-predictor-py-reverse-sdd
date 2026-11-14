"""Logger port — driven port for application-level logging."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Logger(ABC):
    """Port for logging messages from the application core.

    Implementations: LoggingAdapter (wraps stdlib logging), NullLogger (tests).
    """

    @abstractmethod
    def info(self, msg: str, *args: object) -> None:
        """Log an informational message.

        Args:
            msg: Format string (%-style or f-string).
            *args: Format arguments.
        """
        pass

    @abstractmethod
    def warning(self, msg: str, *args: object) -> None:
        """Log a warning message.

        Args:
            msg: Format string.
            *args: Format arguments.
        """
        pass

    @abstractmethod
    def error(self, msg: str, *args: object) -> None:
        """Log an error message.

        Args:
            msg: Format string.
            *args: Format arguments.
        """
        pass

    @abstractmethod
    def exception(self, msg: str, *args: object) -> None:
        """Log an exception with traceback.

        Args:
            msg: Format string.
            *args: Format arguments.
        """
        pass

    @abstractmethod
    def debug(self, msg: str, *args: object) -> None:
        """Log a debug message.

        Args:
            msg: Format string.
            *args: Format arguments.
        """
        pass
