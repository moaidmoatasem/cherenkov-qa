"""Domain models for CC-4 Scheduling and Routines."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RoutineTrigger(BaseModel):
    """Configuration for when a routine runs."""
    type: Literal["cron", "interval", "date", "webhook"]
    value: str  # e.g., "*/5 * * * *" for cron, "3600" for interval
    enabled: bool = True


class Routine(BaseModel):
    """A scheduled background routine."""
    id: str
    name: str
    description: str
    trigger: RoutineTrigger
    target_module: str  # e.g., "cherenkov.scheduling.templates.daily_health_check:run"
    target_kwargs: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_run: datetime | None = None
    next_run: datetime | None = None
    enabled: bool = True


class RunRecord(BaseModel):
    """Execution record for a routine."""
    id: str
    routine_id: str
    status: Literal["success", "failure", "running"]
    start_time: datetime
    end_time: datetime | None = None
    logs: list[str] = Field(default_factory=list)
    error: str | None = None
