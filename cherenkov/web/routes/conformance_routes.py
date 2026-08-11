"""FastAPI routes for query-based conformance status and reports."""
from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(tags=["conformance"])


@router.get("/api/conformance/status")
async def conformance_status(service: str = Query(...)):
    """Return latest conformance status for a service URL.

    Args:
        service: Target service URL query parameter.

    Returns:
        Dictionary summarizing violations, endpoints tested, and status.
    """
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
    """Return detailed conformance report for a service.

    Args:
        service: Target service URL query parameter.

    Returns:
        Detailed conformance report dictionary payload.
    """
    from cherenkov.web.divergences import get_latest_report
    return get_latest_report(service)
