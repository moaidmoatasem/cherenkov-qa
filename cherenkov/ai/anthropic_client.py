"""
CHERENKOV ai/anthropic_client.py — Anthropic Claude InferenceClient.

Supports ANTHROPIC_API_KEY (static key) or ANTHROPIC_BEARER_TOKEN (session
ingress token used in cloud environments) via Bearer auth header.

Used when PROVIDER=anthropic is set.
"""

from __future__ import annotations

import os
import re
import time

from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.ollama_client import strip_think, _try_json
from cherenkov.core.errors import ProviderJSONError, get_logger

_log = get_logger("ANTHROPIC_CLIENT")

_DEFAULT_MODEL = os.getenv("CHERENKOV_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")


class AnthropicInferenceClient(InferenceClient):
    """Anthropic Claude implementation of InferenceClient.

    Auth priority:
      1. ANTHROPIC_BEARER_TOKEN → Authorization: Bearer <token>
      2. ANTHROPIC_API_KEY      → x-api-key header (standard SDK key)
    """

    def __init__(self) -> None:
        self.bearer_token = os.environ.get("ANTHROPIC_BEARER_TOKEN", "")
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._token_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reprompts": 0,
        }

    def _get_client(self):
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from exc
        if self.bearer_token:
            return anthropic.Anthropic(
                api_key="bearer",
                default_headers={"Authorization": f"Bearer {self.bearer_token}"},
            )
        return anthropic.Anthropic(api_key=self.api_key)

    def _complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
    ) -> str:
        t0 = time.time()
        if self.bearer_token:
            # Use httpx directly so we can use Bearer auth without x-api-key interference
            import httpx

            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 4096,
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                timeout=120.0,
            )
            resp.raise_for_status()
            body = resp.json()
            text = body["content"][0]["text"] if body.get("content") else ""
            usage = body.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
        else:
            client = self._get_client()
            message = client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = message.content[0].text if message.content else ""
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens

        elapsed = int((time.time() - t0) * 1000)
        self._token_usage["prompt_tokens"] += input_tokens
        self._token_usage["completion_tokens"] += output_tokens
        _log.info(
            "anthropic completion",
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
        raw = self._complete(system_prompt, user_prompt, model, temperature=temperature)
        code = strip_think(raw)
        # Strip markdown fences if present
        fenced = re.search(r"```(?:typescript|ts)?\s*([\s\S]+?)```", code)
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
        for attempt in range(max_reprompts + 1):
            raw = self._complete(
                system_prompt, user_prompt, model, temperature=temperature
            )
            text = strip_think(raw)
            # Extract JSON
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
            f"Anthropic failed to return valid JSON after {max_reprompts + 1} attempts"
        )
