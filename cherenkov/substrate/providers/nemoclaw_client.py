"""
CHERENKOV ai/nemoclaw_client.py — NVIDIA NemoClaw inference client.

NemoClaw runs Nemotron models locally via the OpenShell runtime, which exposes
an OpenAI-compatible /v1/chat/completions endpoint.  All inference stays on
device (requires_egress=False).  Authentication uses a Bearer token that is
empty by default in development setups.
"""

from __future__ import annotations

from typing import Any

import requests

from cherenkov.core.settings import get_settings
from cherenkov.substrate.providers.openai_compat import OpenAICompatibleClient


class NemoClawInferenceClient(OpenAICompatibleClient):
    """OpenShell-backed inference client for NVIDIA NemoClaw.

    Communicates with the NemoClaw OpenShell runtime, which provides an
    OpenAI-compatible chat completions API with optional policy enforcement
    (network/filesystem isolation, real-time approval for external access).
    """

    provider_label = "NemoClaw"
    log_name = "nemoclaw"
    strips_reasoning = True

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
    ) -> None:
        super().__init__()
        self.base_url = (base_url or get_settings().NEMOCLAW_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else get_settings().NEMOCLAW_API_KEY
        self.timeout = timeout or get_settings().NEMOCLAW_TIMEOUT

    def _post(self, url: str, *, headers: dict, json: dict, timeout: int) -> Any:
        return requests.post(url, headers=headers, json=json, timeout=timeout)

    def _get(self, url: str, *, headers: dict, timeout: int) -> Any:
        return requests.get(url, headers=headers, timeout=timeout)
