import json
import logging
from cherenkov.core.logging_ext import JSONFormatter, setup_json_logging


def test_json_formatter_init():
    fmt = JSONFormatter()
    assert fmt is not None


def test_json_formatter_format_simple_record():
    fmt = JSONFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__,
        lineno=42, msg="hello %s", args=("world",), exc_info=None
    )
    output = fmt.format(record)
    parsed = json.loads(output)
    assert "ts" in parsed
    assert "level" in parsed
    assert "logger" in parsed
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test"
    assert parsed["msg"] == "hello world"


def test_setup_json_logging_returns_none():
    result = setup_json_logging("test-logger", level=10)
    assert result is None


def test_setup_json_logging_creates_handler():
    name = "test-logger-handler"
    setup_json_logging(name, level=10)
    logger = logging.getLogger(name)
    assert logger.handlers
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
