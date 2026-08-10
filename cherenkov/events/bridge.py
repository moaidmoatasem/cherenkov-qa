"""
cherenkov/events/bridge.py
Orchestrator → UnifiedEventBus adapter (ADR-016 wiring).

Converts the OrchestrationEngine's string-key event stream
(_emit_event(name, data)) into CHERENKOVEvent objects and publishes
them to the global UnifiedEventBus so MCP tools and other consumers
can subscribe, persist, or query pipeline telemetry.

Best-effort by design: a failing bus must never take down a pipeline run.
"""

from __future__ import annotations

import logging
from typing import Any

from cherenkov.core.events import CHERENKOVEvent, EventCategory, EventSeverity
from cherenkov.events import get_event_bus

logger = logging.getLogger(__name__)

# Orchestrator event name → UnifiedEventBus category mapping. Names not
# listed fall back to PIPELINE (orchestrator events are pipeline telemetry).
_ORCHESTRATOR_EVENT_CATEGORY: dict[str, EventCategory] = {
    "stage_start": EventCategory.PIPELINE,
    "stage_success": EventCategory.PIPELINE,
    "stage_skip": EventCategory.PIPELINE,
    "test_generated": EventCategory.PIPELINE,
    "replan_trigger": EventCategory.PIPELINE,
    "pipeline_complete": EventCategory.PIPELINE,
}

# Names whose payload carries a failure signal → WARNING/ERROR severity.
_ERROR_NAMES: frozenset[str] = frozenset({"pipeline_complete"})


def to_cherenkov_event(
    name: str, data: dict[str, Any], *, run_id: str = ""
) -> CHERENKOVEvent:
    """Map an orchestrator (name, data) event to a CHERENKOVEvent.

    Args:
        name (str): Orchestrator event name (e.g. stage_start, pipeline_complete).
        data (dict[str, Any]): Event payload data dictionary.
        run_id (str, optional): Correlation ID for the pipeline run. Defaults to "".

    Returns:
        CHERENKOVEvent: Constructed domain event ready for bus publishing.
    """
    category = _ORCHESTRATOR_EVENT_CATEGORY.get(name, EventCategory.PIPELINE)
    payload = dict(data or {})
    success = payload.get("success", True)
    severity = EventSeverity.ERROR if success is False else EventSeverity.INFO
    if name in _ERROR_NAMES and payload.get("success", True) is False:
        severity = EventSeverity.ERROR
    elif any(k in payload for k in ("error", "reason")) and payload.get("success", True) is False:
        severity = EventSeverity.WARNING
    return CHERENKOVEvent(
        category=category,
        name=name,
        payload=payload,
        severity=severity,
        source="orchestrator",
        correlation_id=run_id,
    )


def publish(name: str, data: dict[str, Any], *, run_id: str = "") -> None:
    """Publish an orchestrator event to the global UnifiedEventBus.

    Never raises — bus failures are logged at DEBUG so pipeline runs are
    not affected by telemetry problems.

    Args:
        name (str): Orchestrator event name.
        data (dict[str, Any]): Event payload data dictionary.
        run_id (str, optional): Correlation ID for the pipeline run. Defaults to "".

    Returns:
        None
    """
    try:
        get_event_bus().publish(to_cherenkov_event(name, data, run_id=run_id))
    except Exception:  # pragma: no cover - defensive
        logger.debug("event bus publish skipped (%s)", name, exc_info=True)
