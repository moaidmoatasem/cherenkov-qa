"""Tests for LLM observability tracer."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from cherenkov.observability.llm_tracer import trace_event, _detect_backend


class TestLlmTracer(unittest.TestCase):
    def test_detect_backend_default(self):
        """Default backend should be 'none'."""
        backend = _detect_backend()
        self.assertEqual(backend, "none")

    def test_detect_backend_langsmith(self):
        """Should detect 'langsmith' when env var is set."""
        with patch.dict(os.environ, {"CHERENKOV_LLM_OBSERVABILITY": "langsmith"}):
            backend = _detect_backend()
            self.assertEqual(backend, "langsmith")

    def test_detect_backend_langfuse(self):
        """Should detect 'langfuse' when env var is set."""
        with patch.dict(os.environ, {"CHERENKOV_LLM_OBSERVABILITY": "langfuse"}):
            backend = _detect_backend()
            self.assertEqual(backend, "langfuse")

    def test_trace_event_noop(self):
        """trace_event should silently no-op when no backend is configured."""
        result = trace_event("test-event", key="value")
        self.assertIsNone(result, "trace_event() must return None (fire-and-forget)")

    def test_trace_event_case_insensitive(self):
        """Should handle mixed case backend names."""
        with patch.dict(os.environ, {"CHERENKOV_LLM_OBSERVABILITY": "LangSmith"}):
            backend = _detect_backend()
            # The env var value is lowercased in _detect_backend
            self.assertEqual(backend, "langsmith")

    def test_trace_event_with_attributes(self):
        """Should pass attributes through without error."""
        result = trace_event(
            "eval-complete",
            pass_rate=0.95,
            scenarios=10,
            model="qwen2.5-coder",
        )
        self.assertIsNone(result, "trace_event() must return None")

    def test_trace_event_no_library(self):
        """Should silently handle missing langsmith library."""
        with patch.dict(os.environ, {"CHERENKOV_LLM_OBSERVABILITY": "langsmith"}):
            # langsmith is not installed, so it should silently no-op
            result = trace_event("test", scenario="test")
        self.assertIsNone(
            result, "trace_event() must return None even when library is missing"
        )

    def test_trace_event_multiple_calls(self):
        """Multiple trace_event calls should not interfere."""
        results = [
            trace_event("event1", key="val1"),
            trace_event("event2", key="val2"),
            trace_event("event3"),
        ]
        self.assertTrue(
            all(r is None for r in results), "all trace_event() calls must return None"
        )

    def test_trace_event_special_chars(self):
        """Should handle special characters in event names."""
        result = trace_event("evals-run#1@2026", scenario="test", score=1.0)
        self.assertIsNone(result, "trace_event() with special chars must return None")
