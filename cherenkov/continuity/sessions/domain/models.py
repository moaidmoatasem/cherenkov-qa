"""Session models for cross-device teleport (CC-5)."""
from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel, Field


class TeleportToken(BaseModel):
    token: str = Field(..., description="Unique QR or link token")
    expires_at: datetime.datetime


class SessionSnapshot(BaseModel):
    id: str = Field(..., description="Unique session ID")
    token: TeleportToken | None = None
    state_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
