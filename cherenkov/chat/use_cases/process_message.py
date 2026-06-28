from __future__ import annotations

from typing import Any

from cherenkov.chat.agent import QAChatAgent
from cherenkov.chat.domain.models import Message, Session
from cherenkov.chat.guard import get_guard
from cherenkov.chat.ports.memory import ConversationMemory


class ProcessMessageUseCase:
    """Process a user message through the QA chat agent with safety guard."""

    def __init__(self, memory: ConversationMemory, agent: QAChatAgent):
        self._memory = memory
        self._agent = agent

    def execute(self, session_id: str, content: str) -> dict[str, Any]:
        session = self._memory.get_session(session_id)
        if not session:
            session = Session(session_id=session_id)
            self._memory.create_session(session)

        guard = get_guard()
        guard_result = guard.check_message(content)
        if not guard_result.allowed:
            return {"error": guard_result.reason, "guard": guard_result.to_dict()}

        message = Message(role="user", content=content)
        self._memory.add_message(session_id, message)

        response = self._agent.process(session, content)
        reply = Message(role="assistant", content=str(response))
        self._memory.add_message(session_id, reply)

        guard.record_message(content, response=str(response))

        return {"reply": str(response), "session_id": session_id}
