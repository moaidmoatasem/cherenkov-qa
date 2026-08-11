"""Run history API — exposes RunStore data to the web UI."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

_log = logging.getLogger(__name__)

from cherenkov.persistence.run_store import RunStatus, get_run_store
from cherenkov.web.auth.deps import require_role
from cherenkov.web.auth.models import Role

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


def _record_to_dict(record) -> dict:
    d = {
        "run_id": record.run_id,
        "command": record.command,
        "target_url": record.target_url,
        "spec_hash": record.spec_hash,
        "verdict": record.verdict,
        "divergence_count": record.divergence_count,
        "coverage_pct": record.coverage_pct,
        "duration_ms": record.duration_ms,
        "timestamp": record.timestamp,
        "status": record.status,
        "journey_id": record.journey_id,
        "failure_classification": record.failure_classification,
    }
    try:
        d["step_state"] = json.loads(record.step_state_json or "{}")
    except Exception:
        _log.debug("could not parse run record step_state_json", exc_info=True)
        d["step_state"] = {}
    try:
        meta = json.loads(record.meta_json or "{}")
        if "rich_verdict" in meta:
            d["rich_verdict"] = meta["rich_verdict"]
    except Exception:
        _log.debug("could not parse run record meta_json", exc_info=True)
    return d


def _read_events(run_id: str) -> list[dict]:
    """Replay a run's on-disk event log.

    The live pipeline broadcasts over /ws/live only; a client that connected
    late or dropped has no other way to recover what happened. The orchestrator
    already writes every event to .cherenkov/runs/{run_id}/events.jsonl, so
    replaying that file costs nothing and closes the gap.
    """
    path = Path(".cherenkov") / "runs" / run_id / "events.jsonl"
    if not path.is_file():
        return []
    events: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # A partially-flushed final line is expected while a run is
                # still in flight; skip it rather than failing the request.
                _log.debug("skipping malformed event line in %s", path)
    return events


@router.get("", operation_id="list_runs")
async def list_runs(
    target_url: str | None = Query(default=None),
    command: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    status: RunStatus | None = Query(default=None),
    journey_id: str | None = Query(default=None),
    _: Role = Depends(require_role(Role.viewer)),
):
    """List historical run records matching filter criteria.

    Args:
        target_url: Optional filter by target service URL.
        command: Optional filter by executed command.
        limit: Maximum number of records to return (default 20, max 200).
        status: Optional filter by run status.
        journey_id: Optional filter by journey ID.
        _: Authorization role dependency.

    Returns:
        List of dictionaries containing run record details.
    """
    store = get_run_store()
    records = await asyncio.to_thread(
        store.list, target_url=target_url, command=command, limit=limit,
        status=status, journey_id=journey_id,
    )
    return [_record_to_dict(r) for r in records]


@router.get("/{run_id}", operation_id="get_run")
async def get_run(
    run_id: str,
    _: Role = Depends(require_role(Role.viewer)),
):
    """Retrieve details for a specific run ID.

    Args:
        run_id: Unique identifier of the run.
        _: Authorization role dependency.

    Returns:
        Dictionary payload containing run record details.

    Raises:
        HTTPException: 404 Not Found if run_id does not exist.
    """
    store = get_run_store()
    record = await asyncio.to_thread(store.get, run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    return _record_to_dict(record)


class ClassificationUpdate(BaseModel):
    """Payload schema for updating a run's failure classification."""
    classification: str


@router.patch("/{run_id}/classification", operation_id="update_run_classification")
async def update_run_classification(
    run_id: str,
    payload: ClassificationUpdate,
    _: Role = Depends(require_role(Role.reviewer)),
):
    """Update failure classification for a given run.

    Args:
        run_id: Unique identifier of the run.
        payload: ClassificationUpdate containing the classification label string.
        _: Authorization role dependency.

    Returns:
        Dictionary status payload.

    Raises:
        HTTPException: 422 Unprocessable Entity if classification is invalid, 404 Not Found if run_id does not exist.
    """
    if payload.classification not in ["product_bug", "test_fragility", "flake", ""]:
        raise HTTPException(status_code=422, detail="Invalid classification")
    
    store = get_run_store()
    success = await asyncio.to_thread(
        store.update_classification, run_id, payload.classification
    )
    if not success:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "updated"}


@router.get("/{run_id}/events", operation_id="get_run_events")
async def get_run_events(
    run_id: str,
    _: Role = Depends(require_role(Role.viewer)),
):
    """Replay the event log for a run, live or finished.

    Args:
        run_id: Unique identifier of the run.
        _: Authorization role dependency.

    Returns:
        Dictionary containing run_id, status, and replayed events list.

    Raises:
        HTTPException: 400 Bad Request if run_id is invalid path, 404 Not Found if run does not exist.
    """
    if "/" in run_id or "\\" in run_id or run_id in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid run id")
    events = await asyncio.to_thread(_read_events, run_id)
    record = await asyncio.to_thread(get_run_store().get, run_id)
    if not events and record is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
    return {
        "run_id": run_id,
        "status": record.status if record else "unknown",
        "events": events,
    }
