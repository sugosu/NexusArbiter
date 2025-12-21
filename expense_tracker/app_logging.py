import logging
from typing import Any, Optional


class AppLogger:
    """Thin application logging adapter wrapping the stdlib logging.Logger.

    This class intentionally provides a small, explicit surface (debug/info/warning/error)
    so the rest of the application can depend on a stable logging API without importing
    the stdlib logging module directly.
    """

    def __init__(self, logger_name: Optional[str] = None) -> None:
        """Create or obtain an underlying stdlib Logger.

        Per manifest: do not perform I/O in the constructor. Handlers/formatters should be
        configured by application composition if needed.
        """
        self._logger = logging.getLogger(logger_name or "expense_tracker")

    def debug(self, message: str, data: Optional[Any] = None) -> None:
        """Log a debug-level message, optionally including structured data.

        The adapter prefers to keep things simple: when data is provided it is appended
        to the formatted message using repr() to avoid surprising serialization behavior.
        """
        if data is None:
            self._logger.debug(message)
        else:
            # Keep structured data visible without assuming any serializer/handler.
            self._logger.debug("%s | data=%r", message, data)

    def info(self, message: str, data: Optional[Any] = None) -> None:
        """Log an info-level message, optionally including structured data."""
        if data is None:
            self._logger.info(message)
        else:
            self._logger.info("%s | data=%r", message, data)

    def warning(self, message: str, data: Optional[Any] = None) -> None:
        """Log a warning-level message, optionally including structured data."""
        if data is None:
            self._logger.warning(message)
        else:
            self._logger.warning("%s | data=%r", message, data)

    def error(self, message: str, data: Optional[Any] = None) -> None:
        """Log an error-level message. If an exception-like object is provided include
        its representation so callers can surface exception information without assuming
        an active exception context.
        """
        if data is None:
            self._logger.error(message)
        else:
            # If data is an exception, include its repr to surface exception details.
            # We avoid trying to infer traceback objects or call logging.exception
            # because that relies on an active exception context.
            self._logger.error("%s | data=%r", message, data)
