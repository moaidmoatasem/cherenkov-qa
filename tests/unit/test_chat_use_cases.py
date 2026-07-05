"""tests/unit/test_chat_use_cases.py — chat use-case layer contract.

Both use cases were written against APIs that never existed on their
collaborators (SafetyGuard.check_message/record_message, QAChatAgent.process,
ConversationMemory.create_session(Session) instead of (session_id: str)).
These tests pin the repaired contracts against the real ConversationMemory
Protocol and QAChatAgent.chat signature.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from cherenkov.chat.domain.models import Message, Session
from cherenkov.chat.use_cases.manage_session import ManageSessionUseCase
from cherenkov.chat.use_cases.process_message import ProcessMessageUseCase


class FakeMemory:
    """In-dict ConversationMemory implementing the Protocol's signatures."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(self, session_id: str, persona_id: str = "qa_assistant") -> Session:
        session = Session(session_id=session_id, persona_id=persona_id)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def add_message(self, session_id: str, message: Message) -> None:
        self._sessions[session_id].messages.append(message)

    def get_messages(self, session_id: str, limit: int = 50) -> list[Message]:
        return self._sessions[session_id].messages[-limit:]

    def close_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list_sessions(self, limit: int = 20) -> list[Session]:
        return list(self._sessions.values())[:limit]


def test_process_message_delegates_to_agent_chat():
    agent = MagicMock()
    agent.chat.return_value = Message(role="assistant", content="42 tests passed")
    use_case = ProcessMessageUseCase(memory=FakeMemory(), agent=agent)

    result = use_case.execute("s-1", "how many tests passed?")

    agent.chat.assert_called_once_with("s-1", "how many tests passed?")
    assert result == {"reply": "42 tests passed", "session_id": "s-1"}


def test_manage_session_creates_via_port_with_string_id():
    memory = FakeMemory()
    use_case = ManageSessionUseCase(memory)

    session = use_case.create_session("s-9")

    assert isinstance(session, Session)
    assert session.session_id == "s-9"
    assert use_case.get_session("s-9") is session


def test_manage_session_list_round_trip():
    memory = FakeMemory()
    use_case = ManageSessionUseCase(memory)
    use_case.create_session("a")
    use_case.create_session("b")

    sessions = use_case.list_sessions()

    assert {s.session_id for s in sessions} == {"a", "b"}
    assert use_case.get_session("missing") is None
