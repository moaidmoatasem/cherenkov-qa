from __future__ import annotations

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.core.settings import get_settings
from cherenkov.ai.interface import InferenceClient
from cherenkov.substrate.provider import ProviderCapabilities

class BedrockProvider:
    """Bring-Your-Own-LLM provider for AWS Bedrock (Enterprise)."""
    requires_egress: bool = True
    provider_name: str = "bedrock"

    def __init__(self, client: InferenceClient | None = None):
        # In a real enterprise setup, this client uses boto3 and IAM roles
        self.client = client
        self.model_name = getattr(get_settings(), "BEDROCK_MODEL_ID", "anthropic.claude-v2")

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        if self.client:
            content = self.client.complete(  # type: ignore
                system_prompt="You are a logical AI.",
                user_prompt=request.task,
                model=self.model_name,
            )
        else:
            # Mock implementation for tests
            content = f"AWS Bedrock mock response for: {request.task}"

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
