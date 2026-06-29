"""Resume use case for teleport (CC-5)."""
from __future__ import annotations

from cherenkov.continuity.sessions.domain.models import SessionSnapshot
from cherenkov.continuity.sessions.ports.store import SessionStore


class ResumeSessionUseCase:
    def __init__(self, store: SessionStore):
        self.store = store

    def execute_by_token(self, token_str: str) -> SessionSnapshot | None:
        """Resume a session snapshot using its teleport token."""
        snapshot = self.store.find_by_token(token_str)
        if snapshot:
            # Invalidate the token after it has been successfully used (one-time use)
            snapshot.token = None
            self.store.save(snapshot)
            return snapshot
        return None

    def execute_by_id(self, session_id: str) -> SessionSnapshot | None:
        """Resume a session snapshot using its ID directly."""
        return self.store.load(session_id)
