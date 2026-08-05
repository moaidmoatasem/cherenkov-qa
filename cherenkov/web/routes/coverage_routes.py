"""Coverage map API — spec coverage map + history trend (Phase 14, #770)."""
from __future__ import annotations

from fastapi import APIRouter, Query

from cherenkov.web import coverage_map as coverage_service

router = APIRouter(prefix="/api/v1/coverage", tags=["coverage"])


@router.get("/map", operation_id="get_coverage_map")
async def get_coverage_map():
    """Return per-endpoint spec coverage map for the dashboard."""
    return coverage_service.build_coverage_map()


@router.get("/trend", operation_id="get_coverage_trend")
async def get_coverage_trend(limit: int = Query(default=60, ge=1, le=500)):
    """Return a coverage-pct time-series from persisted run history."""
    return {"points": coverage_service.coverage_trend(limit=limit)}


@router.get("/summary", operation_id="get_coverage_summary")
async def get_coverage_summary():
    """Return a lightweight coverage aggregate for status chips/gauges."""
    summary = coverage_service.CoverageSummary.from_map(
        coverage_service.build_coverage_map()
    )
    return {
        "coveragePct": summary.coverage_pct,
        "openIssueCount": summary.open_issues,
        "testedCount": summary.tested_endpoints,
        "totalEndpoints": summary.total_endpoints,
    }


@router.get(
    "/conformance-trend", operation_id="get_conformance_trend"
)
async def get_conformance_trend(limit: int = Query(default=60, ge=1, le=500)):
    """Return a conformance trend time-series from persisted run history (#767).

    Each point carries a run verdict + divergence count so the dashboard can
    visualize whether the service is drifting toward or away from the spec,
    not just how much surface was probed.
    """
    return {"points": coverage_service.conformance_trend(limit=limit)}


@router.get(
    "/conformance-summary", operation_id="get_conformance_summary"
)
async def get_conformance_summary():
    """Return aggregate conformance counts (pass/warn/fail) + latest run."""
    return coverage_service.conformance_summary()
