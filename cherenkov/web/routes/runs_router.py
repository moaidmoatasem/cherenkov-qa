"""Run history API — exposes RunStore data to the web UI."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query

from cherenkov.persistence.run_store import get_run_store
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
    }
    try:
        meta = json.loads(record.meta_json or "{}")
        if "rich_verdict" in meta:
            d["rich_verdict"] = meta["rich_verdict"]
    except Exception:
        pass
    return d


@router.get("", operation_id="list_runs")
async def list_runs(
    target_url: str | None = Query(default=None),
    command: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    _: Role = require_role("viewer"),
):
    store = get_run_store()
    records = store.list(target_url=target_url, command=command, limit=limit)
    return [_record_to_dict(r) for r in records]


@router.get("/{run_id}", operation_id="get_run")
async def get_run(
    run_id: str,
    _: Role = require_role("viewer"),
):
    store = get_run_store()
    record = store.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
    return _record_to_dict(record)
