"""Web UI Probe API -- surfaces PlaywrightUiProbe results to the dashboard (#882)."""
from __future__ import annotations
import asyncio
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from cherenkov.web.auth.deps import require_role
from cherenkov.web.auth.models import Role

router = APIRouter(prefix="/api/v1/ui-probe", tags=["ui-probe"])


class ProbeRequest(BaseModel):
    """Payload model for running Playwright UI probe checks."""
    target_url: str
    paths: list[str] = ["/"]


@router.post("/run", operation_id="run_ui_probe")
async def run_ui_probe(payload: ProbeRequest, _: Role = Depends(require_role(Role.viewer))) -> dict[str, Any]:
    """Run PlaywrightUiProbe against URLs and return findings.

    Args:
        payload: ProbeRequest payload containing target_url and paths list.
        _: Viewer role authorization dependency.

    Returns:
        Dictionary containing paths probed, total findings, and issue count.

    Raises:
        HTTPException: 503 Service Unavailable if Playwright is not installed.
    """
    try:
        from cherenkov.execution.ui_probe import PlaywrightUiProbe
    except ImportError:
        raise HTTPException(status_code=503, detail="Playwright not installed.")
    probe = PlaywrightUiProbe(timeout_ms=15_000)
    all_findings: list[dict[str, Any]] = []
    for path in payload.paths[:5]:
        url = payload.target_url.rstrip("/") + path
        try:
            raw = await asyncio.to_thread(probe, url)
        except Exception as exc:
            all_findings.append({"url": url, "kind": "UNREACHABLE", "message": str(exc), "detail": url})
            continue
        for kind, message, detail in raw:
            all_findings.append({"url": url, "kind": kind.value if hasattr(kind, "value") else str(kind), "message": message, "detail": detail})
    issue_kinds = {"JS_ERROR", "UNCAUGHT_EXCEPTION", "BROKEN_IMAGE", "EMPTY_BODY", "UNREACHABLE"}
    issues = [f for f in all_findings if f["kind"] in issue_kinds]
    return {"target_url": payload.target_url, "paths_probed": payload.paths[:5], "status": "issues_found" if issues else "clean", "total_findings": len(all_findings), "issue_count": len(issues), "findings": all_findings}


@router.get("/status", operation_id="get_ui_probe_status")
async def get_ui_probe_status(_: Role = Depends(require_role(Role.viewer))) -> dict[str, Any]:
    """Return whether Playwright is available for UI probing.

    Args:
        _: Viewer role authorization dependency.

    Returns:
        Dictionary payload listing availability boolean and backend information.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return {"available": True, "backend": "playwright"}
    except ImportError:
        return {"available": False, "backend": "playwright", "reason": "Playwright not installed", "install_hint": "pip install playwright && playwright install chromium"}
