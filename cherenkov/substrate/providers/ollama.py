from __future__ import annotations

import json

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.core.settings import get_settings
from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.ollama_client import OllamaInferenceClient
from cherenkov.substrate.provider import ProviderCapabilities


class OllamaProvider:
    requires_egress: bool = False
    provider_name: str = "ollama"

    def __init__(self, client: InferenceClient | None = None):
        self.client = client or OllamaInferenceClient()

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        system_prompt = "You are a logical AI."
        user_prompt = request.task

        model = (
            get_settings().TIER_SMALL_MODEL
            if request.capability_tier == "small"
            else get_settings().TIER_DEEP_MODEL
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
                run_id=request.task[:32] if request.task else None,
            )
        else:
            content = self.client.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                run_id=request.task[:32] if request.task else None,
            )

        return ReasoningResult(
            content=content,
            provider=self.provider_name,
            model=model,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            capability_tiers=["small", "deep", "vision"],
            requires_egress=False,
            provider_name=self.provider_name,
        )
