"""
CHERENKOV substrate/providers/fenced_client.py — base for SDK-backed providers.

Anthropic, Bedrock and HuggingFace all speak through a vendor SDK and then need
the same post-processing: strip reasoning, unwrap markdown fences, and reprompt
until the JSON parses. Subclasses supply `_complete()` plus a label and a
default model; everything else is inherited.
"""

from __future__ import annotations

import abc

from cherenkov.core.errors import ProviderJSONError
from cherenkov.substrate.interfaces import InferenceClient
from cherenkov.substrate.text_utils import (
    extract_fenced_code,
    extract_json_text,
    strip_think,
    try_json,
)


class FencedCompletionClient(InferenceClient):
    """InferenceClient whose only provider-specific part is a text completion call."""

    provider_label: str = "provider"
    default_model: str = ""

    def __init__(self) -> None:
        self._token_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reprompts": 0,
        }

    @abc.abstractmethod
    def _complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
    ) -> str:
        """Return the raw model text and update `self._token_usage`."""

    def complete_code(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,  # noqa: ARG002
    ) -> str:
        raw = self._complete(
            system_prompt, user_prompt, model or self.default_model, temperature=temperature
        )
        return extract_fenced_code(strip_think(raw))

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        max_reprompts: int = 2,
        temperature: float = 0.1,
        run_id: str | None = None,  # noqa: ARG002
    ) -> dict:
        model = model or self.default_model
        for _attempt in range(max_reprompts + 1):
            raw = self._complete(system_prompt, user_prompt, model, temperature=temperature)
            parsed = try_json(extract_json_text(strip_think(raw)))
            if parsed is not None:
                return parsed
            self._token_usage["reprompts"] += 1
        raise ProviderJSONError(
            f"{self.provider_label} failed to return valid JSON "
            f"after {max_reprompts + 1} attempts"
        )
