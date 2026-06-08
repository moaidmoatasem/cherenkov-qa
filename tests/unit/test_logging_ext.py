import json
import unittest
from cherenkov.core.logging_ext import JSONFormatter, setup_json_logging


class TestJSONFormatter(unittest.TestCase):
    def test_formatter_init(self):
        fmt = JSONFormatter()
        self.assertIsNotNone(fmt)

    def test_format_simple_record(self):
        fmt = JSONFormatter()
        import logging
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname=__file__,
            lineno=42, msg="hello %s", args=("world",), exc_info=None
        )
        output = fmt.format(record)
        parsed = json.loads(output)
        self.assertIn("ts", parsed)
        self.assertIn("level", parsed)
        self.assertIn("logger", parsed)
        self.assertEqual(parsed["level"], "INFO")
        self.assertEqual(parsed["logger"], "test")
        self.assertEqual(parsed["msg"], "hello world")


class TestSetupJsonLogging(unittest.TestCase):
    def test_setup_json_logging_returns_none(self):
        result = setup_json_logging("test-logger", level=10)
        self.assertIsNone(result)

    def test_setup_json_logging_creates_handler(self):
        import logging
        name = "test-logger-handler"
        setup_json_logging(name, level=10)
        logger = logging.getLogger(name)
        self.assertTrue(logger.handlers)
        self.assertTrue(any(isinstance(h, logging.StreamHandler) for h in logger.handlers))
