"""CHERENKOV web/regenerate.py — Phase 14 auto-regenerate mode (#769).

Decides *when* a conformance drift should trigger a regeneration cycle and,
when the policy fires, dispatches a regenerate work-item via the injected
`regenerate_fn` port (the `CoverageLoop` entry-point in
`cherenkov/sdet/coverage_loop.py`).

This module is a **policy engine + event fan-out** — it does not itself spin
up mock servers. The actual loop execution is delegated so the engine is
deterministic and unit-testable without live infrastructure:

    >>> loop = CoverageLoop(generate_fn, run_fn, repair_fn, correct_mock_url=...)
    >>> mode = AutoRegenerateMode(regenerate_fn=lambda target: loop.run(target))
    >>> decision = mode.evaluate(target_url, store=store)

The `regenerate_fn` default is a no-op that only emits a
`CHERENKOVEvent(category=PIPELINE, name="regenerate.scheduled")` — this lets
the daemon (#765) consume the event later. When a real loop entrypoint is
supplied, calling `evaluate` on a breach synchronously invokes it.

Signal sources (spec-derived, D7):
  * `coverage_map.detect_regressions` — verdict downgrade / coverage drop / spike
  * `coverage_map.conformance_summary` — active divergence count
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from cherenkov.core.events import CHERENKOVEvent, EventCategory, EventSeverity
from cherenkov.ports.notifier import NotifierPort

from cherenkov.web import coverage_map as coverage_service

# A regenerate entrypoint: target_url -> opaque result. Mirrors the
# CoverageLoop.run signature so the daemon can swap it in transparently.
RegenerateFn = Callable[[str], Any]


@dataclass
class RegenPolicy:
    """Policy controlling auto-regenerate triggers.

    Attributes:
        trigger_on:      regression kinds that fire regeneration
                         (verdict_downgrade / coverage_regression /
                          divergence_spike / any).
        min_active_divergences: fire when latest divergence count ≥ this.
        cooldown_seconds:  quiet between two regenerations for the same target.
        max_regenerations:  hard cap per target to prevent runaway loops.
    """

    trigger_on: list[str] = field(
        default_factory=lambda: ["verdict_downgrade", "coverage_regression"]
    )
    min_active_divergences: int = 1
    cooldown_seconds: float = 60.0
    max_regenerations: int = 3


@dataclass
class RegenDecision:
    """Outcome of an `AutoRegenerateMode.evaluate` call."""

    trigger: bool
    target_url: str
    reason: str = ""
    regressions: list[dict[str, Any]] = field(default_factory=list)
    next_run_after: float | None = 0.0
    executed: bool = False
    result: Any = None
    event: CHERENKOVEvent | None = None


def _default_regenerate(target_url: str) -> dict[str, Any]:
    """No-op regenerate entrypoint used when no loop is wired.

    Emits a schedule event (consumed by the SpecGuardian daemon, #765) and
    records the intent without executing real mock-server work.
    """
    return {
        "target_url": target_url,
        "executed": False,
        "reason": "no regenerate_fn wired — event emitted for daemon",
    }


class AutoRegenerateMode:
    """Policy-driven auto-regenerate trigger for conformance drift (#769)."""

    def __init__(
        self,
        regenerate_fn: RegenerateFn | None = None,
        notifiers: list[NotifierPort] | None = None,
        now: float | None = None,
    ) -> None:
        self._regenerate_fn: RegenerateFn = regenerate_fn or _default_regenerate
        self._notifiers: dict[str, NotifierPort] = {n.name: n for n in (notifiers or [])}
        self._regen_counts: dict[str, int] = {}
        self._last_regen: dict[str, float] = {}
        self._now = now

    def register(self, notifier: NotifierPort) -> None:
        self._notifiers[notifier.name] = notifier

    def list_notifiers(self) -> list[str]:
        return list(self._notifiers)

    def evaluate(
        self,
        target_url: str,
        policy: RegenPolicy | None = None,
        *,
        store=None,
    ) -> RegenDecision:
        """Evaluate whether ``target_url`` should trigger a regeneration cycle.

        Returns a `RegenDecision` describing whether to fire, why, and (when
        `trigger=True`) whether the cycle actually executed.
        """
        policy = policy or RegenPolicy()
        now = self._now if self._now is not None else _utc_now()

        regressions = coverage_service.detect_regressions(store=store, limit=200)
        target_regs = [r for r in regressions if r.get("target_url") == target_url]
        summary = coverage_service.conformance_summary(store=store)
        active_div = summary.get("latestDivergenceCount", 0)

        kinds = {r["kind"] for r in target_regs}
        matched_kinds = kinds if "any" in policy.trigger_on else (kinds & set(policy.trigger_on))
        meets_regen_threshold = len(matched_kinds) > 0 and len(target_regs) >= 1
        meets_div_threshold = active_div >= policy.min_active_divergences

        if not (meets_regen_threshold or meets_div_threshold):
            return RegenDecision(
                trigger=False,
                target_url=target_url,
                reason=(
                    f"no breach (regs={len(target_regs)} kinds={sorted(kinds)}, "
                    f"active_div={active_div})"
                ),
            )

        # Cooldown guard.
        last = self._last_regen.get(target_url, 0.0)
        if now - last < policy.cooldown_seconds:
            return RegenDecision(
                trigger=False,
                target_url=target_url,
                reason=f"cooldown ({policy.cooldown_seconds}s) active",
                regressions=target_regs,
                next_run_after=max(0.0, policy.cooldown_seconds - (now - last)),
            )

        # Hard cap to prevent runaway regeneration.
        if self._regen_counts.get(target_url, 0) >= policy.max_regenerations:
            return RegenDecision(
                trigger=False,
                target_url=target_url,
                reason=(
                    f"max_regenerations ({policy.max_regenerations}) reached for target"
                ),
                regressions=target_regs,
            )

        reason = (
            f"breach triggered: {sorted(matched_kinds)} "
            f"(active_div={active_div})"
        )
        event = CHERENKOVEvent(
            category=EventCategory.PIPELINE,
            name="regenerate.scheduled",
            payload={
                "target_url": target_url,
                "reason": reason,
                "regressions": target_regs,
                "policy": {
                    "trigger_on": policy.trigger_on,
                    "min_active_divergences": policy.min_active_divergences,
                },
            },
            severity=EventSeverity.WARNING,
            source="regenerate.AutoRegenerateMode",
        )

        result = self._regenerate_fn(target_url)
        self._last_regen[target_url] = now
        self._regen_counts[target_url] = self._regen_counts.get(target_url, 0) + 1

        for notifier in self._notifiers.values():
            try:
                notifier.notify_event(event)
            except Exception:
                pass

        return RegenDecision(
            trigger=True,
            target_url=target_url,
            reason=reason,
            regressions=target_regs,
            executed=True,
            result=result,
            event=event,
        )


def _utc_now() -> float:
    import time

    return time.time()
