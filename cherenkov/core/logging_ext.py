from __future__ import annotations

import json
import sys
import time
import logging
from typing import Any


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
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
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger(name)
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def get_logger_ext(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        setup_json_logging(name)
    return logger
