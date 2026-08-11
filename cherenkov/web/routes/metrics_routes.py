"""API routes for system and pipeline observability metrics."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("")
async def get_metrics():
    """Retrieve aggregate substrate cost and governance metrics.

    Returns:
        Dictionary containing request count, token cost, and KPI summaries.
    """
    from cherenkov.substrate.accounting import CostAccountant

    accountant = CostAccountant()
    report = accountant.report
    kpi = accountant.get_governance_kpis()
    return {
        "status": "ok",
        "metrics": {
            "requestCount": report.request_count,
            "totalTokens": report.total_tokens,
            "totalCost": report.total_cost,
            "totalDurationMs": report.total_duration_ms,
            "defectEscapeCount": kpi["defect_escape_count"],
            "falsePositiveRate": kpi["false_positive_rate"],
            "maintenanceEfficiency": kpi["maintenance_efficiency"],
        },
    }


@router.get("/pipeline")
def get_pipeline_metrics(last_runs: int = 10):
    """Retrieve summary pipeline execution metrics over recent runs.

    Args:
        last_runs: Number of recent runs to aggregate.

    Returns:
        Dictionary payload containing metrics summary.

    Raises:
        HTTPException: 500 Internal Server Error if metrics loading fails.
    """
    try:
        from cherenkov.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        return {"metrics": collector.get_summary(last_n_runs=last_runs)}
    except Exception:
        raise HTTPException(status_code=500, detail="Could not load metrics") from None


@router.get("/prometheus")
def get_metrics_prometheus():
    """Export system and pipeline metrics in Prometheus text format.

    Returns:
        PlainTextResponse containing Prometheus metrics text.

    Raises:
        HTTPException: 500 Internal Server Error if metrics collection fails.
    """
    from cherenkov.observability.metrics import MetricsCollector

    try:
        collector = MetricsCollector()
        return PlainTextResponse(
            collector.to_prometheus(), media_type="text/plain; version=0.0.4"
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Could not load metrics") from None
