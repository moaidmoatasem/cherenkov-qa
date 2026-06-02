from __future__ import annotations
from typing import Protocol
from pydantic import BaseModel
import json

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.core.config import Config
from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.ollama_client import OllamaInferenceClient
from cherenkov.ai.openai_client import OpenAIInferenceClient


class ProviderCapabilities(BaseModel):
    capability_tiers: list[str]
    requires_egress: bool
    provider_name: str = ""


class ModelProvider(Protocol):
    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        ...

    def capabilities(self) -> ProviderCapabilities:
        ...


class OllamaProvider:
    def __init__(self, client: InferenceClient | None = None):
        self.client = client or OllamaInferenceClient()

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        system_prompt = "You are a logical AI."
        user_prompt = request.task

        model = (
            Config.TIER_SMALL_MODEL
            if request.capability_tier == "small"
            else Config.TIER_DEEP_MODEL
        )

        if request.output_schema:
            user_prompt += (
                f"\n\nPlease output JSON matching this schema: "
                f"{json.dumps(request.output_schema)}"
            )
            content = self.client.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
            )
        else:
            content = self.client.complete_code(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
            )

        return ReasoningResult(
            content=content,
            provider="ollama",
            model=model,
            cost_usd=0.0,
            latency_ms=0,
            cached=False,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            capability_tiers=["small", "deep"],
            requires_egress=False,
            provider_name="ollama",
        )


class OpenAIProvider:
    def __init__(self, client: InferenceClient | None = None):
        self.client = client or OpenAIInferenceClient()

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        system_prompt = "You are a logical AI."
        user_prompt = request.task

        model = Config.OPENAI_MODEL

        if request.output_schema:
            user_prompt += (
                f"\n\nPlease output JSON matching this schema: "
                f"{json.dumps(request.output_schema)}"
            )
            content = self.client.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
            )
        else:
            content = self.client.complete_code(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
            )

        return ReasoningResult(
            content=content,
            provider="openai",
            model=model,
            cost_usd=0.02,
            latency_ms=0,
            cached=False,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            capability_tiers=["small", "deep"],
            requires_egress=True,
            provider_name="openai",
        )


_PROVIDER_CACHE: dict[str, OllamaProvider | OpenAIProvider] = {}


def get_provider(name: str) -> OllamaProvider | OpenAIProvider:
    if name in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[name]
    if name == "ollama":
        p: OllamaProvider | OpenAIProvider = OllamaProvider()
    elif name == "openai":
        p = OpenAIProvider()
    else:
        raise ValueError(f"Unknown provider '{name}'. Expected 'ollama' or 'openai'.")
    _PROVIDER_CACHE[name] = p
    return p


def provider_for_tier(tier: str) -> OllamaProvider | OpenAIProvider:
    if tier == "small":
        return get_provider(Config.TIER_SMALL_PROVIDER)
    elif tier == "deep":
        return get_provider(Config.TIER_DEEP_PROVIDER)
    else:
        raise ValueError(f"Unknown capability tier '{tier}'. Expected 'small' or 'deep'.")
