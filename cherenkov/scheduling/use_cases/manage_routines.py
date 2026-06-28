"""Use cases for Routines."""
from __future__ import annotations

import uuid
from typing import Any

from cherenkov.scheduling.domain.models import Routine, RoutineTrigger
from cherenkov.scheduling.ports.scheduler import SchedulerPort


def create_routine(
    scheduler: SchedulerPort,
    name: str,
    description: str,
    trigger_type: str,
    trigger_value: str,
    target_module: str,
    target_kwargs: dict[str, Any]
) -> Routine:
    """Create and schedule a new routine."""
    routine = Routine(
        id=f"rt_{uuid.uuid4().hex[:8]}",
        name=name,
        description=description,
        trigger=RoutineTrigger(type=trigger_type, value=trigger_value),
        target_module=target_module,
        target_kwargs=target_kwargs
    )
    scheduler.add_routine(routine)
    return routine


def toggle_routine(scheduler: SchedulerPort, routine_id: str, enabled: bool) -> None:
    """Enable or disable a routine."""
    routines = scheduler.list_routines()
    for r in routines:
        if r.id == routine_id:
            r.enabled = enabled
            scheduler.add_routine(r)  # re-add to apply changes
            break
