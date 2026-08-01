"""
CHERENKOV ai/router.py — LEGACY inference provider router.

Deprecated: superseded by cherenkov.substrate.router.SubstrateRouter, which
adds capability-tier routing, run-budget checks, egress policy enforcement,
model certification (E12 gate) and fallback/spillover. This router only
resolves a provider from CHERENKOV_INFERENCE_PROVIDER and forwards the call.

The only remaining production call site is mcp/handlers.py (HITL repair).
Do not add new consumers — prefer SubstrateRouter or cherenkov.ai.get_client().

Anti-lock-in: providers are swappable via config.
Non-Docker fallback: Ollama provider is always available.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.model_runner_client import ModelRunnerClient
from cherenkov.ai.ollama_client import OllamaClient


def _make_anthropic() -> InferenceClient:
    from cherenkov.ai.anthropic_client import AnthropicInferenceClient
    return AnthropicInferenceClient()


def _make_bedrock() -> InferenceClient:
    from cherenkov.ai.bedrock_client import BedrockInferenceClient
    return BedrockInferenceClient()


def _make_huggingface() -> InferenceClient:
    from cherenkov.ai.huggingface_client import HuggingFaceInferenceClient
    return HuggingFaceInferenceClient()


# Add new providers here without touching InferenceRouter.
# TODO(#type-debt): ModelRunnerClient duck-types a narrower interface than InferenceClient
_REGISTRY: dict[str, Callable[[], Any]] = {
    "ollama": OllamaClient,
    "model-runner": ModelRunnerClient,
    "anthropic": _make_anthropic,
    "bedrock": _make_bedrock,
    "huggingface": _make_huggingface,
}


class InferenceRouter:
    def __init__(self, provider: str | None = None):
        self.provider = provider or os.getenv("CHERENKOV_INFERENCE_PROVIDER", "ollama")

    def resolve_client(self) -> InferenceClient:
        factory = _REGISTRY.get(self.provider, OllamaClient)
        return factory()

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        client = self.resolve_client()
        if hasattr(client, "complete"):
            return client.complete(prompt, system_prompt)
        return client.complete_code(
            system_prompt=system_prompt or "",
            user_prompt=prompt,
            model=os.getenv("GEN_MODEL", "qwen2.5-coder:7b"),
        )

    # Alias for backward compatibility (used in mcp/handlers.py)
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return self.complete(prompt, system_prompt)

    def set_provider(self, name: str) -> None:
        self.provider = name


# Alias for backward compatibility (used in mcp/handlers.py)
AIRouter = InferenceRouter
