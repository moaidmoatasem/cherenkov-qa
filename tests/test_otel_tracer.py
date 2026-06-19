"""
tests/test_otel_tracer.py — Unit tests for CherenkovTracer (Issue #457).
Tests no-op mode when disabled and active mode when enabled.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from cherenkov.observability.otel import CherenkovTracer, _is_enabled, OTEL_AVAILABLE


class TestOtelTracer:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("CHERENKOV_OTEL_ENABLED", raising=False)
        assert _is_enabled() is False

    def test_noop_span_when_disabled(self, monkeypatch):
        monkeypatch.setenv("CHERENKOV_OTEL_ENABLED", "false")
        tracer = CherenkovTracer()
        with tracer.span("test.span") as span:
            assert span is None

    def test_span_attributes_when_disabled(self, monkeypatch):
        monkeypatch.setenv("CHERENKOV_OTEL_ENABLED", "false")
        tracer = CherenkovTracer()
        with tracer.span("test.span", {"key": "val"}) as span:
            assert span is None  # attributes are ignored when disabled

    def test_record_llm_usage_noop_when_disabled(self, monkeypatch):
        monkeypatch.setenv("CHERENKOV_OTEL_ENABLED", "false")
        tracer = CherenkovTracer()
        result = tracer.record_llm_usage(None, 100, 50, "test-model")
        # No-op methods must return None and must not raise
        assert result is None

    def test_record_conformance_noop_when_disabled(self, monkeypatch):
        monkeypatch.setenv("CHERENKOV_OTEL_ENABLED", "false")
        tracer = CherenkovTracer()
        result = tracer.record_conformance(None, 3, 15, "v1", "http://localhost")
        # No-op methods must return None and must not raise
        assert result is None

    @pytest.mark.skipif(not OTEL_AVAILABLE, reason="opentelemetry not installed")
    def test_active_span_when_enabled(self, monkeypatch):
        monkeypatch.setenv("CHERENKOV_OTEL_ENABLED", "true")
        with patch("cherenkov.observability.otel._is_enabled", return_value=True):
            with patch("cherenkov.observability.otel.trace") as mock_trace:
                mock_span = mock_trace.get_tracer.return_value.start_as_current_span.return_value.__enter__.return_value
                tracer = CherenkovTracer()
                with tracer.span("cherenkov.test") as span:
                    assert span is mock_span
