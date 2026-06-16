"""LLM observability tracer — LangSmith + LangFuse integration.

Provides simple event-based tracing for eval runs, adversarial scans,
and pipeline LLM calls. Controlled by CHERENKOV_LLM_OBSERVABILITY env var.

Usage:
    from cherenkov.observability.llm_tracer import trace_event
    trace_event("eval-run", {"scenarios": 5, "model": "qwen2.5-coder"})
"""

from __future__ import annotations

import os
from typing import Any


def _detect_backend() -> str:
    return os.getenv("CHERENKOV_LLM_OBSERVABILITY", "none").lower().strip()


def _is_lib_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def trace_event(event_name: str, **attributes: Any) -> None:
    """Log a trace event to the configured backend (LangSmith or LangFuse).

    This is a fire-and-forget call. If no backend is configured or the
    required library is not installed, it silently no-ops.
    """
    backend = _detect_backend()

    if backend == "langsmith":
        _trace_langsmith(event_name, attributes)
    elif backend == "langfuse":
        _trace_langfuse(event_name, attributes)


def _trace_langsmith(event_name: str, attributes: dict[str, Any]) -> None:
    if not _is_lib_available("langsmith"):
        return
    try:
        from langsmith import Client

        client = Client(
            api_url=os.getenv("LANGSMITH_API_URL", "https://api.smith.langchain.com"),
            api_key=os.getenv("LANGSMITH_API_KEY"),
        )
        client.create_run(
            name=event_name,
            run_type="chain",
            inputs=attributes,
            extra={"cherenkov_version": os.getenv("CHERENKOV_VERSION", "unknown")},
        )
    except Exception:
        pass


def _trace_langfuse(event_name: str, attributes: dict[str, Any]) -> None:
    if not _is_lib_available("langfuse"):
        return
    try:
        from langfuse import Langfuse

        client = Langfuse(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        client.trace(name=event_name, metadata=attributes)
    except Exception:
        pass
