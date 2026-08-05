"""Phase 14 alert policies API (#768)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from cherenkov.adapters.notifiers.registry import NotifierRegistry
from cherenkov.web.alerts import AlertEngine, AlertPolicy, AlertResult

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def _engine() -> AlertEngine:
    return AlertEngine(notifiers=NotifierRegistry.from_env()._notifiers.values())


@router.get("/policy", operation_id="get_alert_policy")
async def get_alert_policy():
    """Return the default alert policy thresholds."""
    p = AlertPolicy()
    return {
        "min_divergences": p.min_divergences,
        "min_regressions": p.min_regressions,
        "verdict_severity": p.verdict_severity,
        "cooldown_seconds": p.cooldown_seconds,
    }


@router.post("/evaluate", operation_id="evaluate_alert")
async def evaluate_alert(
    target_url: str,
    min_divergences: int = 1,
    min_regressions: int = 1,
    cooldown_seconds: float = 300.0,
):
    """Evaluate whether ``target_url`` breaches the alert policy and fan out events.

    Delivery to configured notifiers (Slack, Teams, webhook, etc.) is driven by
    env vars (`CHERENKOV_*_WEBHOOK_URL`, etc.) via `NotifierRegistry.from_env()`.
    """
    policy = AlertPolicy(
        min_divergences=max(0, min_divergences),
        min_regressions=max(0, min_regressions),
        cooldown_seconds=cooldown_seconds,
    )
    result: AlertResult = _engine().evaluate(target_url, policy)
    if result.event is not None:
        event = result.event.to_dict()
    else:
        event = None
    return {
        "alerted": result.alerted,
        "target_url": result.target_url,
        "detail": result.detail,
        "regression_count": result.regression_count,
        "active_divergences": result.active_divergences,
        "notified": result.notified,
        "event": event,
    }
