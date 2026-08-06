"""Journey API — the dashboard's single source of truth for the workflow.

The UI used to hardcode its own copy of the loop in four separate arrays, none
of which any backend fact could contradict. These endpoints serve the journey
definitions the engine actually runs, plus live per-step state for a run, so
the stepper reports what happened rather than what it assumes.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cherenkov.journeys import get_journey_registry, rollup_status
from cherenkov.persistence.run_store import get_run_store
from cherenkov.web.auth.deps import require_role
from cherenkov.web.auth.models import Role
from cherenkov.web.routes.deps import ws_event_callback

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/journeys", tags=["journeys"])


class StartJourneyPayload(BaseModel):
    spec_path: str


def _journey_to_dict(journey) -> dict:
    return {
        "id": journey.id,
        "version": journey.version,
        "label": journey.label,
        "description": journey.description,
        "steps": [
            {
                "id": s.id,
                "kind": s.kind,
                "label": s.label,
                "blurb": s.blurb,
                "surface": s.surface,
                "execution": s.execution,
                "requires": s.requires,
                "optional": s.optional,
            }
            for s in journey.execution_order()
        ],
        "stages": journey.stages(),
    }


def _require_journey(journey_id: str):
    journey = get_journey_registry().get(journey_id)
    if journey is None:
        raise HTTPException(status_code=404, detail=f"Journey {journey_id!r} not found")
    return journey


@router.get("", operation_id="list_journeys")
async def list_journeys(_: Role = Depends(require_role(Role.viewer))):
    registry = get_journey_registry()
    default = registry.default()
    return {
        "default": default.id if default else None,
        "journeys": [_journey_to_dict(j) for j in registry.journeys],
    }


# Declared before /{journey_id} so "runs" is not captured as a journey id.
@router.get("/runs/{run_id}", operation_id="get_journey_run")
async def get_journey_run(
    run_id: str,
    _: Role = Depends(require_role(Role.viewer)),
):
    """Per-step state for a run, live or finished.

    This is the polling fallback the WebSocket-only design lacked: a client
    that connected late still gets an accurate picture.
    """
    record = await asyncio.to_thread(get_run_store().get, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")

    try:
        step_state = json.loads(record.step_state_json or "{}")
    except json.JSONDecodeError:
        _log.debug("could not parse step_state_json for run %s", run_id)
        step_state = {}

    journey = get_journey_registry().get(record.journey_id) if record.journey_id else None
    steps: list[dict] = []
    stages: list[dict] = []

    if journey is not None:
        for step in journey.execution_order():
            entry = step_state.get(step.id, {})
            steps.append({
                "id": step.id,
                "label": step.label,
                "surface": step.surface,
                "execution": step.execution,
                # A manual step is never claimed complete by the engine; absent
                # state means not started, not "done".
                "status": entry.get("status", "not_started"),
                "duration_ms": entry.get("duration_ms"),
            })
        by_id = {s["id"]: s for s in steps}
        for stage in journey.stages():
            member_status = [by_id[i]["status"] for i in stage["step_ids"] if i in by_id]
            stages.append({**stage, "status": rollup_status(member_status)})

    return {
        "run_id": record.run_id,
        "journey_id": record.journey_id,
        "status": record.status,
        "verdict": record.verdict,
        "target_url": record.target_url,
        "timestamp": record.timestamp,
        "duration_ms": record.duration_ms,
        "steps": steps,
        "stages": stages,
    }


@router.get("/{journey_id}", operation_id="get_journey")
async def get_journey(
    journey_id: str,
    _: Role = Depends(require_role(Role.viewer)),
):
    return _journey_to_dict(_require_journey(journey_id))


def _run_journey_thread(journey_id: str, spec_path: str, run_id: str) -> None:
    from cherenkov.core.orchestrator import OrchestrationEngine
    try:
        engine = OrchestrationEngine(run_id=run_id, event_callback=ws_event_callback)
        engine.journey_id = journey_id
        engine.run_pipeline(spec_path)
    except Exception as e:  # pragma: no cover - defensive, mirrors ops_routes
        _log.exception("journey run failed")
        ws_event_callback("pipeline_error", {"detail": str(e)})


@router.post("/{journey_id}/runs", operation_id="start_journey_run")
async def start_journey_run(
    journey_id: str,
    payload: StartJourneyPayload,
    _: Role = Depends(require_role(Role.reviewer)),
):
    _require_journey(journey_id)
    if not os.path.exists(payload.spec_path):
        raise HTTPException(status_code=404, detail="Spec file path not found.")

    from cherenkov.core.settings import reset_settings
    reset_settings()

    run_id = str(uuid.uuid4())[:8]
    threading.Thread(
        target=_run_journey_thread,
        args=(journey_id, payload.spec_path, run_id),
        name=f"journey-{run_id}",
        daemon=True,
    ).start()
    # The run record is written by the engine at start, so this id is
    # immediately resolvable via GET /api/v1/journeys/runs/{run_id}.
    return {"run_id": run_id, "journey_id": journey_id, "status": "launched"}
