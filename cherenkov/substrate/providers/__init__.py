"""
cherenkov.substrate.providers — new-style per-provider backend modules.

Migration status (see agent_memory/findings_2026-08-01_dual_ai_routing_layers.md):

- CURRENT forward path per docs/ARCHITECTURE_MAP.md ("New LLM backend"):
  one module per provider (anthropic, nemoclaw, localai, ...) implementing the
  ModelProvider protocol from substrate/provider_base.py.
- PARTIAL wiring: get_provider() in substrate/provider.py lazily routes only
  'anthropic' / 'nemoclaw' (and 'localai' for VLM) to these modules; 'ollama'
  and 'openai' still resolve to the older inline classes defined in
  substrate/provider.py (which add response-cache wrapping + cost/latency
  bookkeeping that the new-style classes here do not).
- DEAD/BROKEN: providers/vlm.py (VLMProvider/VLMResult) is a non-functional
  adapter that calls methods (describe_image/compare_images) that do not exist
  on substrate/vlm_provider.VLMProvider; the router resolves VLM through the
  old-style vlm_provider module, never through this one.

All provider modules here wrap the transport clients (*_client.py files) located alongside them.
This package serves as an orchestration adapter layer bridging transport clients to the CHERENKOV reasoning domain.
"""

from cherenkov.substrate.providers.nemoclaw import NemoClawProvider
from cherenkov.substrate.providers.ollama import OllamaProvider
from cherenkov.substrate.providers.openai import OpenAIProvider
from cherenkov.substrate.providers.vlm import VLMProvider, VLMResult

__all__ = [
    "NemoClawProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "VLMProvider",
    "VLMResult",
]
