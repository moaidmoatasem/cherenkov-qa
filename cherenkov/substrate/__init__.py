# CHERENKOV substrate package (Epoch 1 + Epoch 9 vision).

from cherenkov.substrate.provider import (
    ModelProvider,
    ProviderCapabilities,
    get_provider,
    get_vlm_provider,
    provider_for_tier,
)
from cherenkov.substrate.providers import (
    NemoClawProvider,
)
from cherenkov.substrate.providers import (
    OllamaProvider as OllamaProviderNew,
)
from cherenkov.substrate.providers import (
    OpenAIProvider as OpenAIProviderNew,
)
from cherenkov.substrate.providers import (
    VLMProvider as VLMProviderNew,
)
from cherenkov.substrate.providers import (
    VLMResult as VLMResultNew,
)
from cherenkov.substrate.router import SubstrateRouter, route
from cherenkov.substrate.vlm_provider import (
    VLMProvider as OldVLMProvider,
)
from cherenkov.substrate.vlm_provider import (
    VLMResult as OldVLMResult,
)

# Legacy aliases (backward compat)
OllamaProvider = get_provider("ollama").__class__
OpenAIProvider = get_provider("openai").__class__
VLMProvider = OldVLMProvider
VLMResult = OldVLMResult

__all__ = [
    "ModelProvider",
    "NemoClawProvider",
    "OllamaProvider",
    "OllamaProviderNew",
    "OpenAIProvider",
    "OpenAIProviderNew",
    "ProviderCapabilities",
    "SubstrateRouter",
    "VLMProvider",
    "VLMProviderNew",
    "VLMResult",
    "VLMResultNew",
    "get_provider",
    "get_vlm_provider",
    "provider_for_tier",
    "route",
]
