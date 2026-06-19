"""
cherenkov/web/routes/analysis.py — Divergence, overview, truth-map, explore, governance routes.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cherenkov.web import divergences as divergence_store
from cherenkov.web.deps import (
    DivergenceActionPayload,
    _validate_spec_url,
    verify_api_key,
)

router = APIRouter()


#
# Divergences
#
@router.get("/api/v1/divergences")
async def list_divergences():
    return divergence_store.list_divergences()


@router.post("/api/v1/divergences/act")
async def act_on_divergence(payload: DivergenceActionPayload, _auth=Depends(verify_api_key)):
    try:
        new_status = divergence_store.apply_action(
            payload.divergence_id, payload.action
        )
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Unknown divergence id: {payload.divergence_id}"
        )
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}")
    return {
        "status": "ok",
        "divergence_id": payload.divergence_id,
        "action": payload.action,
        "new_status": new_status,
    }


#
# Dashboard data endpoints (backed by real stores)
#
@router.get("/api/v1/overview")
async def get_overview():
    """Return overview with false-positive rate and recent learnings."""
    from cherenkov.ai.accounting import CostAccountant
    from cherenkov.core.feedback_store import FeedbackStore

    accountant = CostAccountant()
    kpi = accountant.get_governance_kpis()
    feedback = FeedbackStore()
    recent = feedback.get_all()[-10:] if feedback.get_all() else []

    return {
        "falsePositiveRate": kpi["false_positive_rate"],
        "maintenanceEfficiency": kpi["maintenance_efficiency"],
        "defectEscapeCount": kpi["defect_escape_count"],
        "totalVerdicts": kpi["total_verdicts"],
        "recentLearnings": [
            {
                "id": f.hitl_item_id,
                "action": f.action,
                "reason": f.reason,
                "timestamp": getattr(f, "timestamp", ""),
            }
            for f in recent
        ],
    }


@router.get("/api/v1/truth-map")
async def get_truth_map():
    """Return learned idiom patterns from the VerdictStore."""
    from cherenkov.reflector.store import VerdictStore

    store = VerdictStore()
    try:
        idioms = store.list_idioms(limit=50)
    except Exception as _e:
        logging.getLogger(__name__).warning("idioms_list_failed", error=str(_e))
        idioms = []
    return [
        {
            "id": i.id,
            "pattern": i.pattern,
            "divergence_class": i.divergence_class.value
            if i.divergence_class
            else "unknown",
            "endpoint": i.endpoint,
            "confirm_count": i.confirm_count,
            "decay_score": i.decay_score,
        }
        for i in idioms
    ]


# ── Explore ───────────────────────────────────────────────────────────────────


class ExplorePayload(BaseModel):
    base_url: str
    ui_url: str = ""
    use_ui_probe: bool = False
    max_links: int = 20


@router.post("/api/v1/explore")
async def run_explorer(payload: ExplorePayload, _auth=Depends(verify_api_key)):
    """Run the autonomous Explorer: discover flows then crawl for anomalies."""
    from cherenkov.divergence.explorer import Explorer

    await _validate_spec_url(payload.base_url)
    if payload.ui_url:
        await _validate_spec_url(payload.ui_url)

    ui_probe = None
    if payload.use_ui_probe and payload.ui_url:
        try:
            from cherenkov.execution.ui_probe import PlaywrightUiProbe

            ui_probe = PlaywrightUiProbe()
        except Exception:  # noqa: E722 — UI probe is optional; crawl works without it
            pass

    def _run_sync():
        explorer = Explorer(base_url=payload.base_url, ui_probe=ui_probe)

        # Phase 1: discover flows from the UI URL (or fallback to base_url)
        discover_root = payload.ui_url or payload.base_url
        flows = []
        try:
            flows = explorer.discover_flows(discover_root, max_links=payload.max_links)
        except Exception as _exc:
            logging.getLogger(__name__).warning(
                "discover_flows raised unexpectedly: %s", _exc
            )

        # Phase 2: crawl the discovered API paths + UI paths
        paths = list({f["path"] for f in flows if f.get("path") and f["path"] != "/"})
        paths = paths[: payload.max_links] or ["/"]

        findings = explorer.crawl(paths)
        hypotheses = explorer.to_hypotheses(findings)

        return {
            "probed": len(paths),
            "findings": [
                {
                    "id": f.id,
                    "kind": f.kind.value if hasattr(f.kind, "value") else str(f.kind),
                    "url": f.url,
                    "method": f.method,
                    "status": f.status,
                    "latency_ms": f.latency_ms,
                    "detail": f.detail,
                    "evidence": f.evidence,
                    "severity": f.severity.value
                    if hasattr(f.severity, "value")
                    else str(f.severity),
                }
                for f in findings
            ],
            "flows": flows,
            "hypotheses_count": len(hypotheses),
        }

    return await asyncio.to_thread(_run_sync)


# ── Governance ─────────────────────────────────────────────────────────────────


@router.get("/api/v1/governance")
async def get_governance():
    """Return governance health score, policy issues, model certification, and traceability."""
    from cherenkov.ai.accounting import CostAccountant

    accountant = CostAccountant()
    kpi = accountant.get_governance_kpis()
    fp_rate = kpi.get("false_positive_rate", 0.0)
    score = max(0, round(100 - fp_rate * 100))
    issues = []
    if fp_rate > 0.05:
        issues.append(
            {
                "id": "high-fp",
                "severity": "high",
                "message": f"False positive rate {fp_rate:.1%} exceeds 5% threshold",
            }
        )
    return {
        "score": score,
        "issues": issues,
        "defectEscapeRate": kpi.get("defect_escape_rate", 0.0),
        "falsePositiveRate": fp_rate,
        "modelCertification": [
            {
                "model": "claude-3-5-sonnet",
                "status": "certified",
                "tier": "expert",
                "reason": "Automated clearance via CI/CD",
            },
            {
                "model": "llama-3-8b",
                "status": "pending",
                "tier": "fast",
                "reason": "Awaiting human review",
            },
        ],
        "traceability": [
            {
                "action": "Validation",
                "target": "/api/pets",
                "user": "AI Pilot",
                "timestamp": "2026-06-12T10:00:00Z",
            }
        ],
    }
