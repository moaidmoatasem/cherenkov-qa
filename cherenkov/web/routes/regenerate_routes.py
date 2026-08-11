"""Phase 14 auto-regenerate mode API (#769)."""
from __future__ import annotations

from fastapi import APIRouter

from cherenkov.adapters.notifiers.registry import NotifierRegistry
from cherenkov.web.regenerate import AutoRegenerateMode, RegenPolicy

router = APIRouter(prefix="/api/v1/regenerate", tags=["regenerate"])


def _engine() -> AutoRegenerateMode:
    return AutoRegenerateMode(
        notifiers=list(NotifierRegistry.from_env()._notifiers.values())
    )


@router.get("/policy", operation_id="get_regen_policy")
async def get_regen_policy():
    """Return the default auto-regenerate policy.

    Returns:
        Dictionary containing policy settings including trigger_on, min_active_divergences, cooldown_seconds, and max_regenerations.
    """
    p = RegenPolicy()
    return {
        "trigger_on": p.trigger_on,
        "min_active_divergences": p.min_active_divergences,
        "cooldown_seconds": p.cooldown_seconds,
        "max_regenerations": p.max_regenerations,
    }


@router.post("/evaluate", operation_id="evaluate_regenerate")
async def evaluate_regenerate(
    target_url: str,
    trigger_on: list[str] | None = None,
    min_active_divergences: int = 1,
    cooldown_seconds: float = 60.0,
    max_regenerations: int = 3,
):
    """Decide whether ``target_url`` conformance drift should schedule a regenerate.

    The `regenerate_fn` port defaults to a no-op that only emits a
    `regenerate.scheduled` event (consumed by the SpecGuardian daemon, #765).
    Passing a real `CoverageLoop` entrypoint via `AutoRegenerateMode` wires
    synchronous execution instead.

    Args:
        target_url: Target service URL to inspect.
        trigger_on: Optional list of event triggers.
        min_active_divergences: Minimum divergence count to trigger regeneration.
        cooldown_seconds: Cooldown duration in seconds between regenerations.
        max_regenerations: Maximum allowed regeneration count.

    Returns:
        Dictionary payload containing evaluation decision, target URL, reason, and event payload.
    """
    policy = RegenPolicy(
        trigger_on=trigger_on or RegenPolicy().trigger_on,
        min_active_divergences=max(0, min_active_divergences),
        cooldown_seconds=cooldown_seconds,
        max_regenerations=max(1, max_regenerations),
    )
    decision = _engine().evaluate(target_url, policy)
    event = decision.event.to_dict() if decision.event else None
    return {
        "trigger": decision.trigger,
        "target_url": decision.target_url,
        "reason": decision.reason,
        "regressions": decision.regressions,
        "next_run_after": decision.next_run_after,
        "executed": decision.executed,
        "notified": list(_engine().list_notifiers()),
        "event": event,
    }


@router.post("/", operation_id="trigger_regenerate")
async def trigger_regenerate(
    target_url: str,
    reason: str = "manual",
    trigger_on: list[str] | None = None,
    max_regenerations: int = 3,
):
    """Manual trigger for an immediate regenerate cycle on ``target_url``.

    Args:
        target_url: Target service URL to regenerate.
        reason: Reason string for manual trigger invocation.
        trigger_on: Optional list of event triggers.
        max_regenerations: Maximum allowed regeneration attempts.

    Returns:
        Dictionary payload containing trigger result, target URL, execution status, and event payload.
    """
    policy = RegenPolicy(
        trigger_on=trigger_on or RegenPolicy().trigger_on,
        max_regenerations=max(1, max_regenerations),
    )
    mode = AutoRegenerateMode()
    decision = mode.evaluate(target_url, policy)
    if not decision.trigger:
        # Force execution on an explicit manual call even if policy cools-down /
        # caps are hit — the caller is opting in.
        from cherenkov.web.regenerate import _default_regenerate

        mode._regenerate_fn = _default_regenerate  # type: ignore[assignment]
        decision = mode.evaluate(
            target_url,
            RegenPolicy(trigger_on=list(trigger_on) if trigger_on else ["any"]),
        )
    event = decision.event.to_dict() if decision.event else None
    return {
        "trigger": decision.trigger,
        "target_url": decision.target_url,
        "reason": f"manual: {reason}" if reason != "manual" else "manual trigger",
        "executed": decision.executed,
        "result": decision.result,
        "event": event,
    }
