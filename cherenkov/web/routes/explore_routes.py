"""POST /api/v1/explore — crawl a live surface and surface anomalies.

The Explorer observes; it never judges. This endpoint runs a crawl over a
list of paths (HTTP probe + optional Playwright UI probe) and returns raw
findings plus any auto-discovered flows. Findings are evidence for the Triage
workspace; they are *not* auto-confirmed defects.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from cherenkov.divergence.explorer import Explorer
from cherenkov.web.routes.deps import verify_api_key

_log = logging.getLogger(__name__)

router = APIRouter(tags=["explore"])

MAX_PATHS = 100
MAX_DISCOVER = 30


class ExplorePayload(BaseModel):
    """Payload for crawling API surfaces and discovering endpoint flows."""
    base_url: str = Field(default="http://localhost:8000")
    paths: list[str] = Field(default_factory=list)
    method: str = "GET"
    slow_ms: int = 2000
    discover: bool = False


def _validate_payload(payload: ExplorePayload) -> None:
    if not payload.paths:
        raise HTTPException(status_code=422, detail="At least one path is required.")
    if len(payload.paths) > MAX_PATHS:
        raise HTTPException(
            status_code=422, detail=f"Crawl capped at {MAX_PATHS} paths."
        )
    scheme = payload.base_url.split("://", 1)[0].lower() if "://" in payload.base_url else ""
    if scheme and scheme not in ("http", "https"):
        raise HTTPException(
            status_code=422, detail="base_url must use http(s) only."
        )
    if payload.slow_ms < 100:
        raise HTTPException(status_code=422, detail="slow_ms must be at least 100.")


@router.post("/api/v1/explore")
async def explore(payload: ExplorePayload, _auth=Depends(verify_api_key)):
    """Crawl specified endpoints and discover raw findings and candidate flows.

    Args:
        payload: ExplorePayload object containing base_url, paths, method, and options.
        _auth: API key dependency.

    Returns:
        Dictionary payload listing probed count, discovered flows, and raw findings.

    Raises:
        HTTPException: 422 Unprocessable Entity if input validation fails.
    """
    _validate_payload(payload)

    explorer = Explorer(
        base_url=payload.base_url, slow_ms=payload.slow_ms
    )

    discovered: list[dict] = []
    discover_note = ""
    if payload.discover:
        discovered = await asyncio.to_thread(
            explorer.discover_flows, payload.base_url, MAX_DISCOVER
        )
        if not discovered:
            discover_note = (
                "Flow discovery produced no results (Playwright unavailable, "
                "unreachable root, or no crawlable links/forms/nav found)."
            )

    findings = await asyncio.to_thread(
        explorer.crawl, payload.paths, payload.method
    )

    return {
        "base_url": payload.base_url,
        "method": payload.method,
        "probed": len(payload.paths),
        "discovered": discovered,
        "discover_note": discover_note,
        "findings": [f.model_dump() for f in findings],
    }
