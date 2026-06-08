from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Persona:
    persona_id: str
    name: str
    description: str
    system_prompt: str
    tools: list[str] = field(default_factory=list)
    model: str = "qwen2.5-coder:7b"
    temperature: float = 0.1


_DEFAULT_PERSONA = Persona(
    persona_id="qa_assistant",
    name="QA Assistant",
    description="Answers questions about API test results, divergences, and idioms",
    system_prompt=(
        "You are a QA assistant for CHERENKOV, an API conformance testing tool. "
        "Answer questions about test results using the available tools. "
        "Be concise and precise. Reference specific endpoints, status codes, and idioms when relevant."
    ),
    tools=["query_verdicts", "query_idioms", "explain_divergence", "run_test"],
)


class PersonaRegistry:
    def __init__(self):
        self._personas: dict[str, Persona] = {_DEFAULT_PERSONA.persona_id: _DEFAULT_PERSONA}

    def get(self, persona_id: str) -> Persona | None:
        return self._personas.get(persona_id)

    def register(self, persona: Persona) -> None:
        self._personas[persona.persona_id] = persona

    def list_personas(self) -> list[Persona]:
        return list(self._personas.values())

    def compose_prompt(self, persona_id: str, context: dict[str, Any] | None = None) -> str:
        persona = self.get(persona_id)
        if not persona:
            persona = _DEFAULT_PERSONA
        prompt = persona.system_prompt
        if context:
            if "project_context" in context:
                prompt += f"\n\nProject context:\n{context['project_context']}"
            if "idioms" in context:
                idioms_text = "\n".join(f"- {i}" for i in context["idioms"][:10])
                prompt += f"\n\nKnown idioms:\n{idioms_text}"
            if "recent_divergences" in context:
                divs = "\n".join(f"- {d}" for d in context["recent_divergences"][:5])
                prompt += f"\n\nRecent divergences:\n{divs}"
        return prompt
