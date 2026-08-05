"""
CHERENKOV ai/huggingface_client.py — HuggingFace InferenceClient.
"""

from __future__ import annotations

import os
import time

from cherenkov.core.errors import get_logger
from cherenkov.substrate.providers.fenced_client import FencedCompletionClient

_log = get_logger("HUGGINGFACE_CLIENT")

_DEFAULT_MODEL = os.getenv("CHERENKOV_HF_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")


class HuggingFaceInferenceClient(FencedCompletionClient):
    """HuggingFace implementation of InferenceClient."""

    provider_label = "HuggingFace"
    default_model = _DEFAULT_MODEL

    def __init__(self) -> None:
        super().__init__()
        self.token = os.environ.get("HF_TOKEN", "")
        self._client = None

    def _get_client(self):
        if self._client:
            return self._client
        try:
            from huggingface_hub import InferenceClient as HFClient
        except ImportError as exc:
            raise ImportError(
                "huggingface_hub package not installed. Run: pip install huggingface_hub"
            ) from exc

        self._client = HFClient(token=self.token)
        return self._client

    def _complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
    ) -> str:
        t0 = time.monotonic()
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = client.chat_completion(
            model=model, messages=messages, max_tokens=4096, temperature=temperature
        )

        text = response.choices[0].message.content

        # Approximate token usage if not provided natively by the endpoint
        input_tokens = getattr(response.usage, "prompt_tokens", len(user_prompt) // 4)
        output_tokens = getattr(response.usage, "completion_tokens", len(text) // 4)

        elapsed = int((time.monotonic() - t0) * 1000)
        self._token_usage["prompt_tokens"] += input_tokens
        self._token_usage["completion_tokens"] += output_tokens
        _log.info(
            "huggingface completion",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=elapsed,
        )
        return text
