from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("")
async def get_metrics():
    from cherenkov.ai.accounting import CostAccountant

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
    try:
        from cherenkov.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        return {"metrics": collector.get_summary(last_n_runs=last_runs)}
    except Exception:
        raise HTTPException(status_code=500, detail="Could not load metrics")


@router.get("/prometheus")
def get_metrics_prometheus():
    from cherenkov.observability.metrics import MetricsCollector

    try:
        collector = MetricsCollector()
        return PlainTextResponse(
            collector.to_prometheus(), media_type="text/plain; version=0.0.4"
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Could not load metrics")