from __future__ import annotations
from typing import Protocol
from pydantic import BaseModel
import json

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.ai.ollama_client import InferenceClient

class ProviderCapabilities(BaseModel):
    capability_tiers: list[str]
    requires_egress: bool

class ModelProvider(Protocol):
    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        ...

    def capabilities(self) -> ProviderCapabilities:
        ...

class OllamaProvider(ModelProvider):
    def __init__(self, client: InferenceClient):
        self.client = client

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        system_prompt = "You are a logical AI."
        user_prompt = request.task

        # Default model for Ollama in this setup
        model = "qwen2.5-coder:7b" if request.capability_tier == "small" else "deepseek-r1:8b"

        if request.output_schema:
            user_prompt += f"\n\nPlease output JSON matching this schema: {json.dumps(request.output_schema)}"
            response_dict = self.client.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
            )
            content = response_dict
        else:
            response_text = self.client.complete_code(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
            )
            content = response_text

        return ReasoningResult(
            content=content,
            provider="ollama",
            model=model,
            cost_usd=0.0,
            latency_ms=0,
            cached=False
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            capability_tiers=["small", "deep"],
            requires_egress=False
        )
