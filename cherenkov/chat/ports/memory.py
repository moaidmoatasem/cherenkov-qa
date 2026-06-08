from __future__ import annotations

from typing import Protocol

from cherenkov.chat.domain.models import Session, Message


class ConversationMemory(Protocol):
    def create_session(self, session_id: str, persona_id: str = "qa_assistant") -> Session:
        ...

    def get_session(self, session_id: str) -> Session | None:
        ...

    def add_message(self, session_id: str, message: Message) -> None:
        ...

    def get_messages(self, session_id: str, limit: int = 50) -> list[Message]:
        ...

    def close_session(self, session_id: str) -> None:
        ...

    def list_sessions(self, limit: int = 20) -> list[Session]:
        ...
