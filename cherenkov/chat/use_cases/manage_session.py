from __future__ import annotations

from cherenkov.chat.domain.models import Session
from cherenkov.chat.ports.memory import ConversationMemory


class ManageSessionUseCase:
    """Create, retrieve, and manage chat sessions."""

    def __init__(self, memory: ConversationMemory):
        self._memory = memory

    def create_session(self, session_id: str) -> Session:
        session = Session(session_id=session_id)
        self._memory.create_session(session)
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self._memory.get_session(session_id)

    def list_sessions(self, limit: int = 20) -> list[Session]:
        return self._memory.list_sessions(limit=limit)
