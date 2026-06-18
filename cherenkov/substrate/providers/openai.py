from __future__ import annotations


from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.core.settings import get_settings
from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.openai_client import OpenAIInferenceClient
from cherenkov.substrate.provider import ProviderCapabilities


class OpenAIProvider:
    requires_egress: bool = True
    provider_name: str = "openai"

    def __init__(self, client: InferenceClient | None = None):
        self.client = client or OpenAIInferenceClient()

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        content = self.client.complete(  # type: ignore
            system_prompt="You are a logical AI.",
            user_prompt=request.task,
            model=get_settings().OPENAI_MODEL,
        )
        return ReasoningResult(
            content=content,
            provider=self.provider_name,
            model=get_settings().OPENAI_MODEL,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            capability_tiers=["small", "deep"],
            requires_egress=True,
            provider_name=self.provider_name,
        )
