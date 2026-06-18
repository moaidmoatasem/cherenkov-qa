"""
CHERENKOV ai/huggingface_client.py — HuggingFace InferenceClient.
"""

from __future__ import annotations

import os
import re
import time

from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.ollama_client import strip_think, _try_json
from cherenkov.core.errors import ProviderJSONError, get_logger

_log = get_logger("HUGGINGFACE_CLIENT")

_DEFAULT_MODEL = os.getenv("CHERENKOV_HF_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")


class HuggingFaceInferenceClient(InferenceClient):
    """HuggingFace implementation of InferenceClient."""

    def __init__(self) -> None:
        self.token = os.environ.get("HF_TOKEN", "")
        self._token_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reprompts": 0,
        }
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
        t0 = time.time()
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

        elapsed = int((time.time() - t0) * 1000)
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

    def complete_code(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        model = model or _DEFAULT_MODEL
        raw = self._complete(system_prompt, user_prompt, model, temperature=temperature)
        code = strip_think(raw)
        fenced = re.search(r"```(?:typescript|ts|python)?\s*([\s\S]+?)```", code)
        if fenced:
            code = fenced.group(1).strip()
        return code

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        max_reprompts: int = 2,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> dict:
        model = model or _DEFAULT_MODEL
        for attempt in range(max_reprompts + 1):
            raw = self._complete(
                system_prompt, user_prompt, model, temperature=temperature
            )
            text = strip_think(raw)
            fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
            if fenced:
                text = fenced.group(1).strip()
            else:
                start = next((i for i, c in enumerate(text) if c in "{["), None)
                if start is not None:
                    text = text[start:]
            parsed = _try_json(text)
            if parsed is not None:
                return parsed
            self._token_usage["reprompts"] += 1
        raise ProviderJSONError(
            f"HuggingFace failed to return valid JSON after {max_reprompts + 1} attempts"
        )
