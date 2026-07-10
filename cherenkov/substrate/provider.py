from __future__ import annotations
import time
from typing import Any, Protocol
from pydantic import BaseModel
import json

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.core.settings import get_settings
from cherenkov.ai.interface import InferenceClient, CachedInferenceClient
from cherenkov.ai.cache import ResponseCache
from cherenkov.ai.ollama_client import OllamaInferenceClient
from cherenkov.ai.openai_client import OpenAIInferenceClient
from cherenkov.substrate.vlm_provider import VLMProvider


class ProviderCapabilities(BaseModel):
    capability_tiers: list[str]
    requires_egress: bool
    provider_name: str = ""


class ModelProvider(Protocol):
    def generate(self, request: ReasoningRequest) -> ReasoningResult: ...

    def capabilities(self) -> ProviderCapabilities: ...


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


def _wrap_with_cache(client: InferenceClient, provider_name: str) -> InferenceClient:
    cache = shared_response_cache()
    if cache is None:
        return client
    return CachedInferenceClient(client, cache=cache, provider=provider_name)


class OllamaProvider:
    def __init__(self, client: InferenceClient | None = None):
        self.client = (
            _wrap_with_cache(OllamaInferenceClient(), "ollama")
            if client is None
            else client
        )

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

        hits_before = (
            self.client.cache_stats.hits
            if isinstance(self.client, CachedInferenceClient)
            else 0
        )
        t0 = time.monotonic()
        content: dict[str, Any] | str
        if request.output_schema:
            content = self.client.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
            )
        else:
            content = self.client.complete_code(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
            )
        latency_ms = int((time.monotonic() - t0) * 1000)
        cache_hit = (
            isinstance(self.client, CachedInferenceClient)
            and self.client.cache_stats.hits > hits_before
        )

        return ReasoningResult(
            content=content,
            provider="ollama",
            model=model,
            cost_usd=0.0,
            latency_ms=latency_ms,
            cached=cache_hit,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            capability_tiers=["small", "deep"],
            requires_egress=False,
            provider_name="ollama",
        )


class OpenAIProvider:
    def __init__(self, client: InferenceClient | None = None):
        self.client = (
            _wrap_with_cache(OpenAIInferenceClient(), "openai")
            if client is None
            else client
        )

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        system_prompt = "You are a logical AI."
        user_prompt = request.task

        model = get_settings().OPENAI_MODEL

        if request.output_schema:
            user_prompt += (
                f"\n\nPlease output JSON matching this schema: "
                f"{json.dumps(request.output_schema)}"
            )

        hits_before = (
            self.client.cache_stats.hits
            if isinstance(self.client, CachedInferenceClient)
            else 0
        )
        t0 = time.monotonic()
        content: dict[str, Any] | str
        if request.output_schema:
            content = self.client.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
            )
        else:
            content = self.client.complete_code(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
            )
        latency_ms = int((time.monotonic() - t0) * 1000)
        cache_hit = (
            isinstance(self.client, CachedInferenceClient)
            and self.client.cache_stats.hits > hits_before
        )

        return ReasoningResult(
            content=content,
            provider="openai",
            model=model,
            cost_usd=0.0 if cache_hit else 0.02,
            latency_ms=latency_ms,
            cached=cache_hit,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            capability_tiers=["small", "deep"],
            requires_egress=True,
            provider_name="openai",
        )


class GitHubModelsProvider:
    """Free cloud provider via GitHub Models API."""

    def __init__(self, client: InferenceClient | None = None) -> None:
        if client is None:
            from cherenkov.ai.github_models_client import GitHubModelsInferenceClient

            client = _wrap_with_cache(GitHubModelsInferenceClient(), "github")
        self.client = client

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        import json

        model = (
            get_settings().GITHUB_MODELS_SMALL_MODEL
            if request.capability_tier == "small"
            else get_settings().GITHUB_MODELS_DEEP_MODEL
        )
        system_prompt = (
            "You are a logical QA AI assistant specializing in API conformance testing."
        )
        user_prompt = request.task

        if request.output_schema:
            user_prompt += (
                f"\n\nOutput JSON matching: {json.dumps(request.output_schema)}"
            )

        hits_before = (
            self.client.cache_stats.hits
            if isinstance(self.client, CachedInferenceClient)
            else 0
        )
        t0 = time.monotonic()
        content: dict[str, Any] | str
        if request.output_schema:
            content = self.client.complete_json(
                system_prompt=system_prompt, user_prompt=user_prompt, model=model
            )
        else:
            content = self.client.complete_code(
                system_prompt=system_prompt, user_prompt=user_prompt, model=model
            )
        latency_ms = int((time.monotonic() - t0) * 1000)
        cache_hit = (
            isinstance(self.client, CachedInferenceClient)
            and self.client.cache_stats.hits > hits_before
        )

        return ReasoningResult(
            content=content,
            provider="github",
            model=model,
            cost_usd=0.0,
            latency_ms=latency_ms,
            cached=cache_hit,
        )

    def capabilities(self) -> ProviderCapabilities:
        # Note: Excluded 'vision' tier to avoid breaking get_vlm_provider registry
        return ProviderCapabilities(
            capability_tiers=["small", "deep"],
            requires_egress=True,
            provider_name="github",
        )


_PROVIDER_CACHE: dict[str, OllamaProvider | OpenAIProvider | GitHubModelsProvider] = {}
_VLM_CACHE: dict[str, VLMProvider] = {}


def get_provider(name: str) -> OllamaProvider | OpenAIProvider | GitHubModelsProvider:
    if name in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[name]
    if name == "ollama":
        p: OllamaProvider | OpenAIProvider | GitHubModelsProvider = OllamaProvider()
    elif name == "openai":
        p = OpenAIProvider()
    elif name == "github":
        p = GitHubModelsProvider()
    elif name == "anthropic":
        from cherenkov.substrate.providers.anthropic import AnthropicProvider

        p = AnthropicProvider()  # type: ignore[assignment]
    elif name == "nemoclaw":
        from cherenkov.substrate.providers.nemoclaw import NemoClawProvider

        p = NemoClawProvider()  # type: ignore[assignment]
    else:
        raise ValueError(
            f"Unknown provider '{name}'. Expected 'ollama', 'openai', 'github', 'anthropic', or 'nemoclaw'."
        )
    _PROVIDER_CACHE[name] = p
    return p


def get_vlm_provider(name: str | None = None) -> VLMProvider:
    provider_name = name or get_settings().TIER_VISION_PROVIDER
    if provider_name in _VLM_CACHE:
        return _VLM_CACHE[provider_name]
    if provider_name == "localai":
        from cherenkov.substrate.providers.localai import LocalAIVLMProvider

        # TODO(#type-debt): LocalAIVLMProvider duck-types VLMProvider without subclassing
        p: VLMProvider = LocalAIVLMProvider()  # type: ignore[assignment]
    elif provider_name == "ollama":
        p = VLMProvider(OllamaInferenceClient())
    elif provider_name == "openai":
        p = VLMProvider(OpenAIInferenceClient())
    elif provider_name == "nemoclaw":
        from cherenkov.ai.nemoclaw_client import NemoClawInferenceClient

        p = VLMProvider(NemoClawInferenceClient())
    else:
        raise ValueError(
            f"Unknown VLM provider '{provider_name}'. "
            f"Expected 'localai', 'ollama', 'openai', or 'nemoclaw'."
        )
    _VLM_CACHE[provider_name] = p
    return p


def provider_for_tier(
    tier: str, device_class: str | None = None
) -> OllamaProvider | OpenAIProvider | GitHubModelsProvider | VLMProvider:
    if tier == "small":
        return get_provider(get_settings().TIER_SMALL_PROVIDER)
    elif tier == "deep":
        return get_provider(get_settings().TIER_DEEP_PROVIDER)
    elif tier == "vision":
        vlm_provider_name = _resolve_vlm_provider(device_class)
        return get_vlm_provider(vlm_provider_name)
    else:
        raise ValueError(
            f"Unknown capability tier '{tier}'. Expected 'small', 'deep', or 'vision'."
        )


def _resolve_vlm_provider(device_class: str | None = None) -> str:
    configured = get_settings().TIER_VISION_PROVIDER
    if configured != "auto":
        return configured
    from cherenkov.core.devices import DeviceInfo, VLMTier

    info = DeviceInfo()
    if info.vlm_tier == VLMTier.LOCAL:
        return "localai" if info.has_docker else "ollama"
    elif info.vlm_tier == VLMTier.CLOUD:
        return "openai"
    return "ollama"
