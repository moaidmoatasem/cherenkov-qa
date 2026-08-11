"""Spec Guardian API -- exposes DriftStore to the dashboard (Phase 14, #764, #765, #772).

Provides read-only access to real drift events and reports stored by the
SpecGuardianDaemon. No daemon needs to be running to query historical data.
The write side (storing events) is owned by the daemon itself.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Query

from cherenkov.web.auth.deps import require_role
from cherenkov.web.auth.models import Role

router = APIRouter(prefix="/api/v1/guardian", tags=["guardian"])


def _store():
    from cherenkov.spec_guardian.store import DriftStore
    return DriftStore()


@router.get("/status", operation_id="get_guardian_status")
async def get_guardian_status(
    _: Role = Depends(require_role(Role.viewer)),
) -> dict[str, Any]:
    """Return latest drift report summary and trend for the last 24 hours.

    Args:
        _: Required viewer role authorization dependency.

    Returns:
        Dictionary containing latest report model dump and 24h trend list.
    """
    store = _store()

    report = await asyncio.to_thread(store.latest_report)
    trend = await asyncio.to_thread(store.drift_trend, 24)

    return {
        "latest_report": report.to_dict() if report else None,
        "trend_24h": trend,
    }


@router.get("/events", operation_id="list_guardian_events")
async def list_guardian_events(
    limit: int = Query(default=50, ge=1, le=500),
    _: Role = Depends(require_role(Role.viewer)),
) -> list[dict[str, Any]]:
    """Return the most recent drift events (newest first).

    Args:
        limit: Maximum number of drift events to retrieve.
        _: Required viewer role authorization dependency.

    Returns:
        List of drift event dictionaries.
    """
    store = _store()
    events = await asyncio.to_thread(store.recent_events, limit)
    return [e.to_dict() for e in events]


@router.get("/trend", operation_id="get_guardian_trend")
async def get_guardian_trend(
    hours: int = Query(default=24, ge=1, le=168),
    _: Role = Depends(require_role(Role.viewer)),
) -> dict[str, Any]:
    """Return drift trend statistics for the last N hours (default 24, max 168).

    Args:
        hours: Number of hours history to aggregate.
        _: Required viewer role authorization dependency.

    Returns:
        Dictionary containing drift trend metrics.
    """
    store = _store()
    return await asyncio.to_thread(store.drift_trend, hours)
