"""
CHERENKOV ai/openai_client.py — OpenAI provider implementing InferenceClient.

Proves agnosticism: a cloud provider implementing the same SPI as Ollama.
"""

from __future__ import annotations

from cherenkov.core.settings import get_settings
from cherenkov.substrate.providers.openai_compat import OpenAICompatibleClient


class OpenAIInferenceClient(OpenAICompatibleClient):
    """OpenAI-specific implementation of the InferenceClient interface."""

    provider_label = "OpenAI API"
    log_name = "openai"

    def __init__(self):
        super().__init__()
        self.api_key = get_settings().OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"
