# CHERENKOV ai sub-package
from cherenkov.ai.interface import InferenceClient, CachedInferenceClient
from cherenkov.ai.ollama_client import OllamaInferenceClient
from cherenkov.ai.openai_client import OpenAIInferenceClient
from cherenkov.ai.rag_index import RAGIndex
from cherenkov.core.settings import get_settings
from cherenkov.core.contracts import AccountingReport, CacheStats


_current_client: CachedInferenceClient | None = None
_current_provider: str | None = None


def get_client() -> InferenceClient:
    """Return the configured provider client based on get_settings().PROVIDER.

    The client is **memoized per provider**: repeated calls within a run reuse the
    same CachedInferenceClient so its response cache and cost accounting persist
    across stages/scenarios (previously every call rebuilt the client, silently
    discarding the cache and resetting accounting to the last call only). When
    get_settings().PROVIDER changes, the client is rebuilt for the new provider.

    Use set_client()/reset_client() for explicit injection in tests.
    """
    global _current_client, _current_provider
    provider = get_settings().PROVIDER.lower().strip()

    if _current_client is not None and _current_provider == provider:
        return _current_client

    if provider == "ollama":
        raw_client = OllamaInferenceClient()
    elif provider == "openai":
        raw_client = OpenAIInferenceClient()  # type: ignore
    elif provider == "nemoclaw":
        from cherenkov.ai.nemoclaw_client import NemoClawInferenceClient

        raw_client = NemoClawInferenceClient()  # type: ignore
    elif provider == "anthropic":
        from cherenkov.ai.anthropic_client import AnthropicInferenceClient

        raw_client = AnthropicInferenceClient()  # type: ignore
    else:
        raise ValueError(
            f"Unknown provider '{provider}'. Expected 'ollama', 'openai', 'nemoclaw', or 'anthropic'."
        )

    _current_client = CachedInferenceClient(raw_client)
    _current_provider = provider
    return _current_client


def set_client(client: CachedInferenceClient | None) -> None:
    """Inject a client explicitly (e.g. a CachedInferenceClient wrapping a mock).

    Marks the provider as unknown so the next get_settings().PROVIDER-driven get_client()
    call rebuilds rather than handing back the injected client for a mismatched
    provider.
    """
    global _current_client, _current_provider
    _current_client = client
    _current_provider = None


def reset_client() -> None:
    """Clear the memoized client. Next get_client() builds fresh from Config."""
    global _current_client, _current_provider
    _current_client = None
    _current_provider = None


def get_accounting_report() -> AccountingReport | None:
    """Return the current client's accounting report if active."""
    if _current_client is not None:
        return _current_client.accounting_report
    return None


def get_cache_stats() -> CacheStats | None:
    """Return the current client's cache statistics if active."""
    if _current_client is not None:
        return _current_client.cache_stats
    return None


__all__ = [
    "InferenceClient",
    "CachedInferenceClient",
    "OllamaInferenceClient",
    "OpenAIInferenceClient",
    "RAGIndex",
    "get_client",
    "set_client",
    "reset_client",
    "get_accounting_report",
    "get_cache_stats",
]
