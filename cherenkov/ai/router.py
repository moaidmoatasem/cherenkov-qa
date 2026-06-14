"""
CHERENKOV ai/router.py — Inference provider router.
Authority: v3.1 + delta.

Anti-lock-in: providers are swappable via config.
Non-Docker fallback: Ollama provider is always available.
"""

from __future__ import annotations

import os

from cherenkov.ai.ollama_client import OllamaClient
from cherenkov.ai.model_runner_client import ModelRunnerClient
from cherenkov.ai.interface import InferenceClient


class InferenceRouter:
    def __init__(self, provider: str | None = None):
        self.provider = provider or os.getenv("CHERENKOV_INFERENCE_PROVIDER", "ollama")

    def resolve_client(self) -> InferenceClient:
        if self.provider == "model-runner":
            return ModelRunnerClient()
        if self.provider == "anthropic":
            from cherenkov.ai.anthropic_client import AnthropicInferenceClient
            return AnthropicInferenceClient()
        if self.provider == "bedrock":
            from cherenkov.ai.bedrock_client import BedrockInferenceClient
            return BedrockInferenceClient()
        if self.provider == "huggingface":
            from cherenkov.ai.huggingface_client import HuggingFaceInferenceClient
            return HuggingFaceInferenceClient()
        return OllamaClient()

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        client = self.resolve_client()
        if hasattr(client, "complete"):
            return client.complete(prompt, system_prompt)
        return client.complete_code(
            system_prompt=system_prompt or "",
            user_prompt=prompt,
            model=os.getenv("GEN_MODEL", "qwen2.5-coder:7b"),
        )

    def set_provider(self, name: str) -> None:
        self.provider = name
