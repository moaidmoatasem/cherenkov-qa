# CHERENKOV substrate package (Epoch 1 + Epoch 9 vision).

from cherenkov.substrate.provider import (
    ModelProvider,
    OllamaProvider,
    OpenAIProvider,
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

# Legacy aliases (backward compat) — direct class references only.
# NOTE: previously computed as get_provider("ollama").__class__, which
# instantiated real provider clients (and possibly the shared response cache)
# at import time. Direct re-export of the provider.py classes is identical.
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
