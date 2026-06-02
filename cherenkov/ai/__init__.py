# CHERENKOV ai sub-package
from cherenkov.ai.interface import InferenceClient, CachedInferenceClient
from cherenkov.ai.ollama_client import OllamaInferenceClient
from cherenkov.ai.openai_client import OpenAIInferenceClient
from cherenkov.core.config import Config
from cherenkov.core.contracts import AccountingReport, CacheStats


_current_client: CachedInferenceClient | None = None


def get_client() -> InferenceClient:
    """Return the configured provider client based on Config.PROVIDER."""
    global _current_client
    provider = Config.PROVIDER.lower().strip()
    if provider == "ollama":
        raw_client = OllamaInferenceClient()
    elif provider == "openai":
        raw_client = OpenAIInferenceClient()
    else:
        raise ValueError(f"Unknown provider '{provider}'. Expected 'ollama' or 'openai'.")
    
    _current_client = CachedInferenceClient(raw_client)
    return _current_client


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
    "get_client",
    "get_accounting_report",
    "get_cache_stats",
]
