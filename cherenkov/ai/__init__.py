# CHERENKOV ai sub-package
from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.ollama_client import OllamaInferenceClient
from cherenkov.ai.openai_client import OpenAIInferenceClient
from cherenkov.core.config import Config


def get_client() -> InferenceClient:
    """Return the configured provider client based on Config.PROVIDER."""
    provider = Config.PROVIDER.lower().strip()
    if provider == "ollama":
        return OllamaInferenceClient()
    elif provider == "openai":
        return OpenAIInferenceClient()
    else:
        raise ValueError(f"Unknown provider '{provider}'. Expected 'ollama' or 'openai'.")


__all__ = [
    "InferenceClient",
    "OllamaInferenceClient",
    "OpenAIInferenceClient",
    "get_client",
]
