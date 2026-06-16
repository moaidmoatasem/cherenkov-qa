"""
cherenkov/observability/otel.py — OpenTelemetry tracer for CHERENKOV pipeline.
Issue #457: OTLP export for Datadog/Grafana/Jaeger.

Usage:
    from cherenkov.observability.otel import CherenkovTracer, setup_otel_provider
    setup_otel_provider()
    tracer = CherenkovTracer()
    with tracer.span("cherenkov.validate") as span:
        ...
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


def _is_enabled() -> bool:
    return os.getenv("CHERENKOV_OTEL_ENABLED", "false").lower() == "true" and OTEL_AVAILABLE


def setup_otel_provider() -> None:
    """Initialize the global OTEL tracer provider. Call once at startup."""
    if not _is_enabled():
        return

    endpoint = os.getenv("CHERENKOV_OTEL_ENDPOINT", "http://localhost:4317")
    service_name = os.getenv("CHERENKOV_OTEL_SERVICE_NAME", "cherenkov")
    environment = os.getenv("CHERENKOV_OTEL_ENVIRONMENT", "production")

    resource = Resource.create({
        "service.name": service_name,
        "deployment.environment": environment,
    })
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def get_tracer():
    """Return a tracer, or None if OTEL is disabled/unavailable.

    When disabled, callers never touch the tracer: ``CherenkovTracer.span``
    short-circuits and yields ``None``. Returning ``None`` here keeps the
    disabled path free of any ``opentelemetry`` import (it is an optional dep).
    """
    if not _is_enabled():
        return None
    return trace.get_tracer("cherenkov")


class CherenkovTracer:
    """Thin wrapper around OTEL tracer for CHERENKOV pipeline stages."""

    def __init__(self):
        self._tracer = get_tracer()

    @contextmanager
    def span(self, name: str, attributes: dict[str, Any] | None = None) -> Generator:
        """Context manager that yields an OTEL span (or None if disabled)."""
        if not _is_enabled():
            yield None
            return
        with self._tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, v)
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                raise

    def record_llm_usage(self, span, input_tokens: int, output_tokens: int,
                         model: str, cost_usd: float | None = None) -> None:
        if span is None:
            return
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.input_tokens", input_tokens)
        span.set_attribute("llm.output_tokens", output_tokens)
        if cost_usd is not None:
            span.set_attribute("llm.cost_usd", cost_usd)

    def record_conformance(self, span, violations: int, endpoints_tested: int,
                           spec_version: str, target_url: str) -> None:
        if span is None:
            return
        span.set_attribute("cherenkov.violations", violations)
        span.set_attribute("cherenkov.endpoints_tested", endpoints_tested)
        span.set_attribute("cherenkov.spec_version", spec_version)
        span.set_attribute("cherenkov.target_url", target_url)
