from __future__ import annotations

from typing import Protocol

from cherenkov.chat.domain.models import Message, Session


class ConversationMemory(Protocol):
    """Placeholder docstring.

<description>"""
    def create_session(
        """Placeholder docstring.

:param session_id: <description>
:param persona_id: <description>
:return: <description>"""
        self, session_id: str, persona_id: str = "qa_assistant"
    ) -> Session: ...

    def get_session(self, session_id: str) -> Session | None: ...
        """Placeholder docstring.

:param session_id: <description>
:return: <description>"""

    def add_message(self, session_id: str, message: Message) -> None: ...
        """Placeholder docstring.

:param session_id: <description>
:param message: <description>
:return: <description>"""

    def get_messages(self, session_id: str, limit: int = 50) -> list[Message]: ...
        """Placeholder docstring.

:param session_id: <description>
:param limit: <description>
:return: <description>"""

    def close_session(self, session_id: str) -> None: ...
        """Placeholder docstring.

:param session_id: <description>
:return: <description>"""

    def list_sessions(self, limit: int = 20) -> list[Session]: ...
        """Placeholder docstring.

:param limit: <description>
:return: <description>"""
