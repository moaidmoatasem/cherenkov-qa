from __future__ import annotations

import json
import logging
import uuid
from typing import Any, AsyncGenerator

from cherenkov.chat.domain.models import Session, Message
from cherenkov.chat.ports.memory import ConversationMemory
from cherenkov.chat.persona import PersonaRegistry
from cherenkov.chat.guard import get_guard

logger = logging.getLogger(__name__)


class QAChatAgent:
    def __init__(
        self,
        memory: ConversationMemory,
        persona_registry: PersonaRegistry | None = None,
        substrate_router=None,
    ):
        self.memory = memory
        self.persona_registry = persona_registry or PersonaRegistry()
        self.substrate_router = substrate_router

    def create_session(self, persona_id: str = "qa_assistant") -> Session:
        session_id = str(uuid.uuid4())
        return self.memory.create_session(session_id, persona_id)

    def get_session(self, session_id: str) -> Session | None:
        return self.memory.get_session(session_id)

    def add_user_message(self, session_id: str, content: str) -> Message:
        msg = Message(role="user", content=content, session_id=session_id)
        self.memory.add_message(session_id, msg)
        return msg

    def _call_llm(self, messages: list[dict]) -> str:
        if self.substrate_router:
            from cherenkov.core.contracts import ReasoningRequest

            req = ReasoningRequest(task=json.dumps(messages), capability_tier="small")
            result = self.substrate_router.route(req)
            return str(result.content)
        return self._fallback_llm(messages)

    def _fallback_llm(self, messages: list[dict]) -> str:
        logger.error("substrate_router_unavailable")
        user_content = " ".join(
            m.get("content", "") for m in messages if m.get("role") == "user"
        ).lower()
        if "verdict" in user_content:
            return "[MOCK] No verdicts found in the current session. Run a pipeline to generate test verdicts."
        if "idiom" in user_content:
            return "[MOCK] No idioms found in the current session. Run a pipeline to build an idiom library."
        if "divergence" in user_content:
            return "[MOCK] No divergences detected in the current run. Spec and server appear in sync."
        return "[MOCK] AI substrate unavailable. Start Ollama with: ollama serve"

    def _prepare_llm_context(self, session_id: str) -> list[dict]:
        history = self.memory.get_messages(session_id)
        session = self.memory.get_session(session_id)
        persona_id = session.persona_id if session else "qa_assistant"
        persona = self.persona_registry.get(persona_id)
        context = self._build_context(session_id)
        system_prompt = self.persona_registry.compose_prompt(
            persona.persona_id if persona else "qa_assistant",
            context,
        )
        llm_messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            llm_messages.append({"role": msg.role, "content": msg.content})
        return llm_messages

    def chat(self, session_id: str, user_message: str) -> Message:
        self.add_user_message(session_id, user_message)
        llm_messages = self._prepare_llm_context(session_id)
        response_content = self._call_llm(llm_messages)
        get_guard().record_llm_call(llm_messages, response_content)
        assistant_msg = Message(
            role="assistant", content=response_content, session_id=session_id
        )
        self.memory.add_message(session_id, assistant_msg)
        return assistant_msg

    async def chat_stream(
        self, session_id: str, user_message: str
    ) -> AsyncGenerator[str, None]:
        self.add_user_message(session_id, user_message)
        llm_messages = self._prepare_llm_context(session_id)
        full_content = self._call_llm(llm_messages)
        get_guard().record_llm_call(llm_messages, full_content)
        words = full_content.split()
        for i, word in enumerate(words):
            token = word + (" " if i < len(words) - 1 else "")
            yield token
        assistant_msg = Message(
            role="assistant", content=full_content, session_id=session_id
        )
        self.memory.add_message(session_id, assistant_msg)

    def _build_context(self, session_id: str) -> dict[str, Any]:
        context: dict[str, Any] = {}
        try:
            from cherenkov.reflector.reflector import get_reflector

            r = get_reflector()
            stats = r.get_stats()
            context["idioms"] = stats.get("recent_idioms", [])[:10]
        except Exception as e:
            logger.debug(
                "Could not build reflector context for session %s: %s", session_id, e
            )
        return context
