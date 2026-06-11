"""
CHERENKOV ai/github_models_client.py — GitHub Models free cloud provider.

Subclasses OpenAIInferenceClient. Changes ONLY:
  - base_url → https://models.inference.ai.azure.com
  - api_key  → CHERENKOV_GITHUB_TOKEN or GITHUB_TOKEN (auto-provided in CI)
"""
from __future__ import annotations

import os

from cherenkov.ai.openai_client import OpenAIInferenceClient


class GitHubModelsInferenceClient(OpenAIInferenceClient):
    """OpenAI-compatible client pointed at GitHub Models free inference API."""

    def __init__(self) -> None:
        super().__init__()
        self.base_url = os.getenv(
            "CHERENKOV_GITHUB_MODELS_URL",
            "https://models.inference.ai.azure.com",
        )
        self.api_key = (
            os.getenv("CHERENKOV_GITHUB_TOKEN")
            or os.getenv("GITHUB_TOKEN")
            or ""
        )
