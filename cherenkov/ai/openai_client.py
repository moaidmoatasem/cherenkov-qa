"""
CHERENKOV ai/openai_client.py — OpenAI provider implementing InferenceClient.
Authority: v3.1 + delta.

Proves agnosticism: a cloud provider implementing the same SPI as Ollama.
"""

from __future__ import annotations

import re
import time

import requests

from cherenkov.core.errors import ProviderJSONError, get_logger
from cherenkov.core.settings import get_settings
from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.ollama_client import _try_json, _json_repair


class OpenAIInferenceClient(InferenceClient):
    """OpenAI-specific implementation of the InferenceClient interface."""

    def __init__(self):
        self.api_key = get_settings().OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"
        self._token_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reprompts": 0,
        }

    def _chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
        response_format: dict | None = None,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        if response_format:
            body["response_format"] = response_format

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=body,
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        self._token_usage["prompt_tokens"] = usage.get("prompt_tokens", 0)
        self._token_usage["completion_tokens"] = usage.get("completion_tokens", 0)
        return data["choices"][0]["message"]["content"]

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
        log = get_logger("openai", run_id)
        attempt = 0
        last_raw = ""

        while attempt <= max_reprompts:
            t0 = time.time()
            try:
                last_raw = self._chat_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
            except requests.RequestException as e:
                attempt += 1
                if attempt > max_reprompts:
                    raise ProviderJSONError(
                        f"OpenAI API request failed after {max_reprompts} retries: {e}"
                    ) from e
                continue

            dt_ms = int((time.time() - t0) * 1000)
            parsed = _try_json(last_raw) or _json_repair(last_raw)
            if parsed is not None:
                log.info("json ok", model=model, attempt=attempt, duration_ms=dt_ms)
                return parsed

            attempt += 1
            log.warning(
                "json invalid, reprompting",
                model=model,
                attempt=attempt,
                duration_ms=dt_ms,
            )

        raise ProviderJSONError(
            f"{model} did not return valid JSON after {max_reprompts} reprompts. "
            f"Last 200 chars: {last_raw[:200]!r}"
        )

    def complete_code(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        log = get_logger("openai", run_id)
        t0 = time.time()
        text = self._chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
        ).strip()
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        log.info("code ok", model=model, duration_ms=int((time.time() - t0) * 1000))
        return text.strip()

    def complete_vision(
        self,
        system_prompt: str,
        user_prompt: str,
        image_data: str,
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        """Vision request: send image as base64 data URI to OpenAI."""
        log = get_logger("openai-vision", run_id)
        t0 = time.time()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_data}"},
                        },
                    ],
                },
            ],
            "temperature": temperature,
        }
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=body,
            timeout=300,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        log.info("vision ok", model=model, duration_ms=int((time.time() - t0) * 1000))
        return text

    def chat(
        self,
        messages: list[dict],
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        log = get_logger("openai-chat", run_id)
        t0 = time.time()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=body,
            timeout=300,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        log.info("chat ok", model=model, duration_ms=int((time.time() - t0) * 1000))
        return text
