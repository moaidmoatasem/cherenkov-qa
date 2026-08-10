"""CHERENKOV web/alerts.py — Phase 14 alert policies (#768).

A thin policy layer over the conformance surface. Rather than invent a new
notification transport, this module reuses the existing adapter stack:

  * `cherenkov.core.events.CHERENKOVEvent` + `EventSeverity`  (event contract)
  * `cherenkov.ports.notifier.NotifierPort`                   (delivery port)
  * `cherenkov.adapters.notifiers.registry.NotifierRegistry`  (env-driven dispatcher)
  * `cherenkov.web.coverage_map.detect_regressions`           (signal source)

`AlertEngine` decides *whether* a conformation breach crosses a policy
threshold and, if so, fans the resulting event out to every registered
notifier. Delivery itself stays suggest/report-only — this module never
performs side-effects beyond emitting the event envelope and recording the
alert decision, so it is safe to call from a poll or a webhook without
risking runaway notifications.

Thresholds are spec-derived (divergence counts come from RunStore records;
verdict ranks from `verdict/models.py`), per the D7 invariant.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from cherenkov.core.events import CHERENKOVEvent, EventCategory, EventSeverity
from cherenkov.ports.notifier import NotifierPort
from cherenkov.web import coverage_map as coverage_service


@dataclass
class AlertPolicy:
    """Configuration for when a conformance breach becomes an alert.

    Attributes:
        min_divergences:    alert when the latest run reports ≥ this many active
                            divergence findings.
        min_regressions:    alert when `detect_regressions` returns ≥ this many
                            regression events (verdict downgrade / coverage
                            regression / divergence spike).
        verdict_severity:   minimum EventSeverity to attach to the emitted event.
        cooldown_seconds:   minimum quiet between two alerts for the same target.
    """

    min_divergences: int = 1
    min_regressions: int = 1
    verdict_severity: str = "warning"
    cooldown_seconds: float = 300.0


@dataclass
class AlertResult:
    """Outcome of an `AlertEngine.evaluate` call."""

    alerted: bool
    target_url: str
    event: CHERENKOVEvent | None = None
    detail: str = ""
    regression_count: int = 0
    active_divergences: int = 0
    notified: dict[str, bool] = field(default_factory=dict)


_SEVERITY_RANK = {"debug": 0, "info": 1, "warning": 2, "error": 3}


class AlertEngine:
    """Evaluate conformance status against policies and fan out events."""

    def __init__(
        self,
        notifiers: Iterable[NotifierPort] | None = None,
        now: float | None = None,
    ) -> None:
        """Initialize AlertEngine with optional notifiers and clock override.

        Args:
            notifiers: Optional iterable of NotifierPort adapter instances.
            now: Optional fixed timestamp for deterministic testing.
        """
        self._notifiers: dict[str, NotifierPort] = {n.name: n for n in (notifiers or [])}
        # In-process cooldown tracking keyed by target_url. Sufficient for a
        # localhost-first engine; production would persist this in a TTL store.
        self._last_alert: dict[str, float] = {}
        self._now = now

    # ── port registration ───────────────────────────────────────────────────

    def register(self, notifier: NotifierPort) -> None:
        """Register a notification delivery port adapter.

        Args:
            notifier: NotifierPort instance to add to engine.
        """
        self._notifiers[notifier.name] = notifier

    def list_notifiers(self) -> list[str]:
        """List registered notifier names.

        Returns:
            List of registered notifier name strings.
        """
        return list(self._notifiers)

    # ── policy evaluation ───────────────────────────────────────────────────

    def evaluate(
        self,
        target_url: str,
        policy: AlertPolicy | None = None,
        *,
        store=None,
    ) -> AlertResult:
        """Decide whether ``target_url`` breaches ``policy`` and, if so, emit
        an event to every registered notifier.

        Does **not** raise on notifier failure: delivery is best-effort and the
        per-notifier outcome is recorded in `AlertResult.notified`.

        Args:
            target_url: Target API base URL string.
            policy: Optional AlertPolicy threshold configuration.
            store: Optional custom RunStore instance.

        Returns:
            AlertResult detailing evaluation decision and notification status.
        """
        policy = policy or AlertPolicy()

        regressions = coverage_service.detect_regressions(store=store, limit=200)
        target_regressions = [r for r in regressions if r.get("target_url") == target_url]
        # Active divergence count for the target across all recorded runs.
        active = coverage_service.conformance_summary(store=store)
        regen_count = len(target_regressions)

        breaches: list[str] = []
        if regen_count >= policy.min_regressions:
            breaches.append(f"{regen_count} regression(s) for target")
        if active.get("latestDivergenceCount", 0) >= policy.min_divergences:
            breaches.append(f"{active['latestDivergenceCount']} active divergence(s)")

        if not breaches:
            return AlertResult(
                alerted=False,
                target_url=target_url,
                detail="no policy breach",
                regression_count=regen_count,
                active_divergences=active.get("latestDivergenceCount", 0),
            )

        # Cooldown — one alert per target within the policy window.
        ts = self._now if self._now is not None else _utc_now()
        last = self._last_alert.get(target_url, 0.0)
        if ts - last < policy.cooldown_seconds:
            return AlertResult(
                alerted=False,
                target_url=target_url,
                detail=f"cooldown ({policy.cooldown_seconds}s) active",
                regression_count=regen_count,
                active_divergences=active.get("latestDivergenceCount", 0),
            )

        severity = EventSeverity(
            _clamp_severity(policy.verdict_severity, EventSeverity.WARNING)
        )
        event = CHERENKOVEvent(
            category=EventCategory.SYSTEM,
            name="conformance.drift",
            payload={
                "service": target_url,
                "breaches": breaches,
                "regression_count": regen_count,
                "latest_divergence_count": active.get("latestDivergenceCount", 0),
                "latest_verdict": active.get("latestVerdict"),
            },
            severity=severity,
            source="alerts.AlertEngine",
        )

        notified: dict[str, bool] = {}
        for name, notifier in self._notifiers.items():
            try:
                notifier.notify_event(event)
                notified[name] = True
            except Exception:
                notified[name] = False

        self._last_alert[target_url] = ts
        return AlertResult(
            alerted=True,
            target_url=target_url,
            event=event,
            detail="; ".join(breaches),
            regression_count=regen_count,
            active_divergences=active.get("latestDivergenceCount", 0),
            notified=notified,
        )


def _clamp_severity(requested: str, default: EventSeverity) -> str:
    rank = _SEVERITY_RANK.get((requested or "").lower())
    if rank is None:
        return default.value
    names = {v: k for k, v in _SEVERITY_RANK.items()}
    # Map rank → canonical severity name at or just above the requested level.
    for target_rank in sorted(names):
        if target_rank >= rank:
            return names[target_rank]
    return names[max(names)]


def _utc_now() -> float:
    import time

    return time.time()
