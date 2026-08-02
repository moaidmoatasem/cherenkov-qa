"""cherenkov/substrate/provider_base.py — shared types for substrate providers.

Split out of provider.py so that individual provider modules (e.g.
providers/anthropic.py, providers/nemoclaw.py) can depend on the common
provider contract and shared response cache without importing provider.py
itself, which lazily imports those same provider modules inside
get_provider()/get_vlm_provider() and would otherwise form an import cycle.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.core.settings import get_settings
from cherenkov.substrate.cache import ResponseCache
from cherenkov.substrate.interfaces import CachedInferenceClient, InferenceClient


class ProviderCapabilities(BaseModel):
    capability_tiers: list[str]
    requires_egress: bool
    provider_name: str = ""


class ModelProvider(Protocol):
    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        pass

    def capabilities(self) -> ProviderCapabilities:
        pass


_SHARED_RESPONSE_CACHE: ResponseCache | None = None


def shared_response_cache() -> ResponseCache | None:
    """Prefix cache shared across substrate providers, gated by CACHE_ENABLED.

    Identical (model, system_prompt, user_prompt) requests are common across
    certification gold-set runs and repeated healing/repair attempts; a single
    cache instance lets those calls skip the network round-trip entirely
    instead of re-running inference for output we already have.
    """
    global _SHARED_RESPONSE_CACHE
    settings = get_settings()
    if not settings.CACHE_ENABLED:
        return None
    if _SHARED_RESPONSE_CACHE is None:
        _SHARED_RESPONSE_CACHE = ResponseCache(
            max_size=settings.CACHE_MAX_SIZE,
            ttl_seconds=settings.CACHE_TTL_SECONDS,
        )
    return _SHARED_RESPONSE_CACHE


def wrap_with_cache(client: InferenceClient, provider_name: str) -> InferenceClient:
    cache = shared_response_cache()
    if cache is None:
        return client
    return CachedInferenceClient(client, cache=cache, provider=provider_name)
