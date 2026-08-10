"""
cherenkov/core/logging_ext.py — JSON structured logging extensions.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any


class JSONFormatter(logging.Formatter):
    """Custom logging Formatter that outputs log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string.

        Args:
            record (logging.LogRecord): Log record instance to format.

        Returns:
            str: JSON string representation of the log record.
        """
        log_entry: dict[str, Any] = {
            "ts": round(time.time(), 3),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
        if record.exc_info and record.exc_info[0]:
            log_entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_json_logging(name: str = "cherenkov", level: int = logging.INFO) -> None:
    """Configure stream handler with JSONFormatter for specified logger.

    Args:
        name (str, optional): Logger name string. Defaults to "cherenkov".
        level (int, optional): Logging level threshold. Defaults to logging.INFO.

    Returns:
        None
    """
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger(name)
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def get_logger_ext(name: str) -> logging.Logger:
    """Retrieve or initialize a logger instance configured with JSON logging.

    Args:
        name (str): Logger name string.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        setup_json_logging(name)
    return logger

