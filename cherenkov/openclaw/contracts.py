from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class OpenClawConfig(BaseModel):
    """Configuration for the OpenClaw Tier-1 adapter."""
    host: str = "127.0.0.1"
    port: int = 8721
    notification_endpoint: str | None = None
    poll_interval_sec: float = 5.0
    max_notify_retries: int = 3


class TriggerRequest(BaseModel):
    """Request to trigger a re-run from an external voice layer."""
    run_id: str | None = None
    endpoint: str | None = None
    method: str | None = None
    reason: str = "manual_trigger"
    params: dict[str, Any] = Field(default_factory=dict)


class ClassificationRequest(BaseModel):
    """Tier-2 healing feedback classification request."""
    item_id: str
    classification: Literal["regression", "intended", "ignore"]
    actor: str = "unknown"
    detail: str = ""
