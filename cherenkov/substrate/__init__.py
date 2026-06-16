# CHERENKOV substrate package (Epoch 1 + Epoch 9 vision).

from cherenkov.substrate.provider import (
    ModelProvider,
    ProviderCapabilities,
    get_provider,
    get_vlm_provider,
    provider_for_tier,
)
from cherenkov.substrate.vlm_provider import (
    VLMProvider as OldVLMProvider,
    VLMResult as OldVLMResult,
)
from cherenkov.substrate.router import SubstrateRouter, route
from cherenkov.substrate.providers import (
    OllamaProvider as OllamaProviderNew,
    OpenAIProvider as OpenAIProviderNew,
    VLMProvider as VLMProviderNew,
    VLMResult as VLMResultNew,
    NemoClawProvider,
)

# Legacy aliases (backward compat)
OllamaProvider = get_provider("ollama").__class__
OpenAIProvider = get_provider("openai").__class__
VLMProvider = OldVLMProvider
VLMResult = OldVLMResult

__all__ = [
    "ModelProvider",
    "ProviderCapabilities",
    "OllamaProvider",
    "OpenAIProvider",
    "VLMProvider",
    "VLMResult",
    "get_provider",
    "get_vlm_provider",
    "provider_for_tier",
    "SubstrateRouter",
    "route",
    "OllamaProviderNew",
    "OpenAIProviderNew",
    "VLMProviderNew",
    "VLMResultNew",
    "NemoClawProvider",
]
