"""API routes for Scheduling and Routines."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from cherenkov.scheduling.adapters.apscheduler_adapter import APSchedulerAdapter
from cherenkov.scheduling.domain.models import Routine
from cherenkov.scheduling.use_cases.manage_routines import create_routine, toggle_routine

router = APIRouter(prefix="/routines", tags=["routines"])

# Global scheduler instance for now
scheduler = APSchedulerAdapter()


@router.on_event("startup")
async def startup_event():
    scheduler.start()


@router.on_event("shutdown")
async def shutdown_event():
    scheduler.stop()


@router.get("/")
def get_routines() -> list[Routine]:
    """List all registered routines."""
    return scheduler.list_routines()


@router.post("/")
def api_create_routine(
    name: str,
    description: str,
    trigger_type: str,
    trigger_value: str,
    target_module: str,
    target_kwargs: dict[str, Any]
) -> Routine:
    """Create a new routine."""
    return create_routine(
        scheduler, name, description, trigger_type, trigger_value, target_module, target_kwargs
    )


@router.post("/{routine_id}/toggle")
def api_toggle_routine(routine_id: str, enabled: bool) -> dict[str, str]:
    """Toggle a routine on or off."""
    toggle_routine(scheduler, routine_id, enabled)
    return {"status": "ok"}


@router.post("/{routine_id}/run")
def api_run_routine(routine_id: str) -> dict[str, str]:
    """Trigger a routine immediately."""
    scheduler.trigger_routine_now(routine_id)
    return {"status": "triggered"}
