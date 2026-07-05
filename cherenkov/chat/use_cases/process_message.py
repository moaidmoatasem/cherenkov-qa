from __future__ import annotations

from typing import Any

from cherenkov.chat.agent import QAChatAgent
from cherenkov.chat.ports.memory import ConversationMemory


class ProcessMessageUseCase:
    """Process a user message through the QA chat agent.

    Thin application-layer wrapper: QAChatAgent.chat() already owns
    get-or-create session, user/assistant message persistence, the LLM
    call, and guard recording (get_guard().record_llm_call).
    """

    def __init__(self, memory: ConversationMemory, agent: QAChatAgent):
        self._memory = memory
        self._agent = agent

    def execute(self, session_id: str, content: str) -> dict[str, Any]:
        reply = self._agent.chat(session_id, content)
        return {"reply": reply.content, "session_id": session_id}
