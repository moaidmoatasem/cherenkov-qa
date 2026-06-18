from __future__ import annotations

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.core.settings import get_settings
from cherenkov.ai.interface import InferenceClient
from cherenkov.substrate.provider import ProviderCapabilities

class AzureOpenAIProvider:
    """Bring-Your-Own-LLM provider for Azure OpenAI (Enterprise)."""
    requires_egress: bool = True
    provider_name: str = "azure"

    def __init__(self, client: InferenceClient | None = None):
        # In a real enterprise setup, this client handles Azure AD Auth, endpoint, and api-version
        self.client = client
        self.model_name = getattr(get_settings(), "AZURE_OPENAI_DEPLOYMENT", "gpt-4-turbo")

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        if self.client:
            content = self.client.complete(  # type: ignore
                system_prompt="You are a logical AI.",
                user_prompt=request.task,
                model=self.model_name,
            )
        else:
            # Mock implementation for tests
            content = f"Azure OpenAI mock response for: {request.task}"

        return ReasoningResult(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            capability_tiers=["small", "deep", "vision"],
            requires_egress=True,
            provider_name=self.provider_name,
        )
