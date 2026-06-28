"""Session Store Port (CC-5)."""
from __future__ import annotations

import abc

from cherenkov.continuity.sessions.domain.models import SessionSnapshot


class SessionStore(abc.ABC):
    @abc.abstractmethod
    def save(self, snapshot: SessionSnapshot) -> None:
        """Save a session snapshot."""

    @abc.abstractmethod
    def load(self, session_id: str) -> SessionSnapshot | None:
        """Load a session snapshot by ID."""

    @abc.abstractmethod
    def list_sessions(self) -> list[SessionSnapshot]:
        """List all available session snapshots."""

    @abc.abstractmethod
    def find_by_token(self, token_str: str) -> SessionSnapshot | None:
        """Find a snapshot by its teleport token."""
