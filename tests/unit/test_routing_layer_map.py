"""tests/unit/test_routing_layer_map.py — pins the dual AI-routing-layer map (#815).

Guard tests documenting which path is current vs legacy so a future
consolidation changes them deliberately:

- substrate routing resolves through cherenkov.substrate.provider (the
  Epoch-1 factory) for ollama; the new-style class in
  cherenkov.substrate.providers.ollama is NOT what the router uses.
- VLM resolution returns the old-style VLMProvider (substrate.vlm_provider),
  never the new-style providers/vlm.VLMProvider adapter.
- cherenkov.ai.get_client() remains the current direct-client factory.
- cherenkov.substrate.OllamaProvider is the provider.py class (direct
  re-export; importing cherenkov.substrate must not instantiate clients).

See agent_memory/findings_2026-08-01_dual_ai_routing_layers.md.
"""

from unittest.mock import patch

from cherenkov.core.settings import get_settings
from cherenkov.substrate import OllamaProvider as SubstrateOllamaProvider
from cherenkov.substrate.client_factory import CachedInferenceClient, get_client, reset_client
from cherenkov.substrate.interfaces import InferenceClient
from cherenkov.substrate.provider import (
    OllamaProvider as FactoryOllamaProvider,
)
from cherenkov.substrate.provider import (
    get_vlm_provider,
    provider_for_tier,
)
from cherenkov.substrate.providers.ollama import (
    OllamaProvider as NewStyleOllamaProvider,
)
from cherenkov.substrate.vlm_provider import VLMProvider as OldVLMProvider


def test_new_style_ollama_provider_is_distinct_from_factory():
    assert NewStyleOllamaProvider is not FactoryOllamaProvider


def test_router_resolves_ollama_through_provider_py_factory():
    with patch.object(get_settings(), "TIER_SMALL_PROVIDER", "ollama"):
        p = provider_for_tier("small")
    assert isinstance(p, FactoryOllamaProvider)


def test_vlm_resolution_returns_old_style_vlm_provider():
    with patch.object(get_settings(), "TIER_VISION_PROVIDER", "ollama"):
        p = get_vlm_provider()
    assert isinstance(p, OldVLMProvider)


def test_ai_get_client_is_current_direct_factory():
    reset_client()
    try:
        with patch.object(get_settings(), "PROVIDER", "ollama"):
            client = get_client()
        assert isinstance(client, CachedInferenceClient)
        assert isinstance(client, InferenceClient)
    finally:
        reset_client()


def test_substrate_ollama_alias_is_provider_py_class():
    assert SubstrateOllamaProvider is FactoryOllamaProvider
