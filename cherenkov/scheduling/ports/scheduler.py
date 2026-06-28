"""Scheduler Port for CC-4."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from cherenkov.scheduling.domain.models import Routine


@runtime_checkable
class SchedulerPort(Protocol):
    """Protocol for the underlying job scheduler (e.g. APScheduler)."""

    def start(self) -> None:
        """Start the scheduler daemon."""
        ...

    def stop(self) -> None:
        """Stop the scheduler daemon."""
        ...

    def add_routine(self, routine: Routine) -> None:
        """Add or update a routine in the scheduler."""
        ...

    def remove_routine(self, routine_id: str) -> None:
        """Remove a routine from the scheduler."""
        ...

    def list_routines(self) -> list[Routine]:
        """List all registered routines."""
        ...

    def trigger_routine_now(self, routine_id: str) -> None:
        """Trigger an immediate run of a routine."""
        ...
