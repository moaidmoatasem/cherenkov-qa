"""Step registry — maps a journey step's ``kind`` to the code that runs it.

The orchestrator used to name its stages by calling them in a fixed order, so
adding or reordering a stage meant editing the pipeline body. Here a step is
looked up by kind, which is what lets a journey YAML describe a workflow the
engine has never seen as a literal call sequence.

Handlers are deliberately thin: they adapt an existing stage to the step
protocol and nothing more. The retry, fallback and circuit-breaking behaviour
still lives in StageExecutor, where it already was.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from cherenkov.journeys.contracts import JourneyStep, StepStatus


@dataclass
class StepContext:
    """What a step handler is given."""

    engine: Any                 # OrchestrationEngine
    step: JourneyStep
    spec_path: str
    # Carries stage outputs between steps (ingest -> plan -> scenarios).
    state: dict[str, Any] = field(default_factory=dict)
    simulate_fail_stage: str | None = None


@dataclass
class StepOutcome:
    status: StepStatus
    duration_ms: int = 0
    # Shown to the user as "ABORTED: {reason}" when a required step fails.
    reason: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in ("complete", "skipped")


StepHandler = Callable[[StepContext], StepOutcome]
class StepRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, StepHandler] = {}

    def register(self, kind: str, handler: StepHandler) -> None:
        self._handlers[kind] = handler

    def get(self, kind: str) -> StepHandler | None:
        return self._handlers.get(kind)

    def kinds(self) -> list[str]:
        return sorted(self._handlers)
_registry = StepRegistry()


def get_step_registry() -> StepRegistry:
    return _registry


def register_step(kind: str) -> Callable[[StepHandler], StepHandler]:
    def decorator(handler: StepHandler) -> StepHandler:
        _registry.register(kind, handler)
        return handler
    return decorator
