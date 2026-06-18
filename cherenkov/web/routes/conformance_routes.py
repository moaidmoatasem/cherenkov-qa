from fastapi import APIRouter, Query

router = APIRouter(tags=["conformance"])


@router.get("/api/conformance/status")
async def conformance_status(service: str = Query(...)):
    """Return latest conformance status for a service URL."""
    from cherenkov.web.divergences import get_latest_status
    status = get_latest_status(service)
    return {
        "service": service,
        "violations": status.drift_count if status else 0,
        "endpointsTested": status.endpoints_tested if status else 0,
        "lastChecked": status.run_at.isoformat() if status else None,
        "status": "pass" if (status and status.drift_count == 0) else "fail",
    }


@router.get("/api/conformance/report")
async def conformance_report(service: str = Query(...)):
    """Return detailed conformance report for a service."""
    from cherenkov.web.divergences import get_latest_report
    report = get_latest_report(service)
    return report
