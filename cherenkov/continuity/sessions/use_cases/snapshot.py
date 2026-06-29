"""Snapshot use case for teleport (CC-5)."""
from __future__ import annotations

import datetime
import secrets
import string
from typing import Any

from cherenkov.continuity.sessions.domain.models import SessionSnapshot, TeleportToken
from cherenkov.continuity.sessions.ports.store import SessionStore


def generate_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class SnapshotSessionUseCase:
    def __init__(self, store: SessionStore):
        self.store = store

    def execute(self, session_id: str, state_data: dict[str, Any]) -> SessionSnapshot:
        """Create a new session snapshot and generate a teleport token."""
        # Use an expiration of 15 minutes for the teleport token
        expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)
        token = TeleportToken(token=generate_token(), expires_at=expires_at)

        snapshot = SessionSnapshot(
            id=session_id,
            token=token,
            state_data=state_data
        )
        self.store.save(snapshot)
        return snapshot
