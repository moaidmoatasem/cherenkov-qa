"""
CHERENKOV ai/ollama_client.py — the single doorway to local models.

Enforces the decisions that took the whole spec arc to settle:
  - JSON forced at the GPU (format="json"), not begged for in the prompt (D-9)
  - the retry ladder: format=json -> validate -> json-repair -> reprompt(<=2) -> raise
  - the SYSTEM PROMPT is a passed-in constant; callers MUST keep it byte-identical
    across a loop so Ollama's RadixAttention caches the prefix (Delta V1 / D-10)
  - brutal <think> strip for deepseek planning output (don't rescue malformed)
"""

from __future__ import annotations

import json
import re
import time

import requests
import random as _random

from cherenkov.core.errors import OllamaJSONError, get_logger
from cherenkov.core.settings import get_settings
from cherenkov.ai.interface import InferenceClient


def _post_with_retry(
    url: str, payload: dict, timeout: int, max_retries: int = 4
) -> "requests.Response":
    """POST with exponential backoff retry on Timeout or ConnectionError."""
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            return requests.post(url, json=payload, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
            if attempt < max_retries - 1:
                wait = (2**attempt) * 0.5 + _random.uniform(0, 0.5)
                time.sleep(wait)
    if last_err is None:
        raise RuntimeError("_post_with_retry called with max_retries=0")
    raise last_err


class OllamaClient(InferenceClient):
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
        return complete_json(
            system_prompt,
            user_prompt,
            model,
            max_reprompts=max_reprompts,
            temperature=temperature,
            run_id=run_id,
        )

    def complete_code(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        max_reprompts: int = 2,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        return complete_code(
            system_prompt,
            user_prompt,
            model,
            max_reprompts=max_reprompts,
            temperature=temperature,
            run_id=run_id,
        )

    def chat(
        self,
        messages: list[dict],
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        return _DEFAULT_CLIENT.chat(
            messages=messages, model=model, temperature=temperature, run_id=run_id
        )


_THINK = re.compile(r"<think\b[^>]*>.*?</think>", re.DOTALL)


def strip_think(text: str) -> str:
    """Remove deepseek <think> blocks. Malformed/unclosed -> return as-is + caller
    logs a warning. We do NOT try to rescue half-open reasoning (Delta)."""
    return _THINK.sub("", text).strip()


def _try_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _json_repair(raw: str) -> dict | None:
    """Extract the last valid JSON object from a string (last is usually the real response)."""
    # Find all {...} blocks and return the last one (most likely the real response)
    matches = list(re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}", raw, re.DOTALL))
    if matches:
        return _try_json(matches[-1].group(0))
    return None


class OllamaInferenceClient(InferenceClient):
    """Ollama-specific implementation of the InferenceClient interface."""

    def __init__(self) -> None:
        # Populated after each call so CachedInferenceClient can read real counts.
        self._token_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reprompts": 0,
        }

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
        """Return a parsed JSON object from the model, or raise OllamaJSONError.

        `system_prompt` MUST be a stable constant per loop (prefix cache). All the
        per-call variation goes in `user_prompt`.
        """
        log = get_logger("ollama", run_id)
        attempt = 0
        last_raw = ""
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "reprompts": 0}

        while attempt <= max_reprompts:
            t0 = time.time()
            resp = _post_with_retry(
                get_settings().OLLAMA_URL,
                {
                    "model": model,
                    "system": system_prompt,  # static -> cached prefix
                    "prompt": user_prompt,
                    "format": "json",  # constrain sampling to valid JSON (D-9)
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                get_settings().OLLAMA_TIMEOUT,
            )
            resp.raise_for_status()
            body = resp.json()
            last_raw = body.get("response", "")
            dt_ms = int((time.time() - t0) * 1000)

            # Capture real token counts from Ollama response fields
            self._token_usage["prompt_tokens"] = body.get("prompt_eval_count", 0)
            self._token_usage["completion_tokens"] = body.get("eval_count", 0)

            parsed = _try_json(last_raw) or _json_repair(last_raw)
            if parsed is not None:
                log.info("json ok", model=model, attempt=attempt, duration_ms=dt_ms)
                return parsed

            attempt += 1
            self._token_usage["reprompts"] = attempt
            log.warning(
                "json invalid, reprompting",
                model=model,
                attempt=attempt,
                duration_ms=dt_ms,
            )

        raise OllamaJSONError(
            f"{model} did not return valid JSON after {max_reprompts} reprompts. "
            f"Last 200 chars: {last_raw[:200]!r}"
        )

    def complete_code(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        max_reprompts: int = 2,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        """For the GENERATE stage: we want raw TS code, not JSON. Same static-prompt
        discipline for prefix caching. Strips stray markdown fences."""
        log = get_logger("ollama", run_id)
        attempt = 0
        text = ""
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "reprompts": 0}
        while attempt <= max_reprompts:
            t0 = time.time()
            resp = _post_with_retry(
                get_settings().OLLAMA_URL,
                {
                    "model": model,
                    "system": system_prompt,
                    "prompt": user_prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                get_settings().OLLAMA_TIMEOUT,
            )
            resp.raise_for_status()
            body = resp.json()
            text = body.get("response", "").strip()
            self._token_usage["prompt_tokens"] = body.get("prompt_eval_count", 0)
            self._token_usage["completion_tokens"] = body.get("eval_count", 0)
            text = re.sub(r"^```[a-z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()
            log.info(
                "code ok",
                model=model,
                attempt=attempt,
                duration_ms=int((time.time() - t0) * 1000),
            )
            if text:
                return text
            attempt += 1
            self._token_usage["reprompts"] = attempt
            log.warning(
                "empty code response, reprompting", model=model, attempt=attempt
            )
        return text

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
        """Vision request: send image as base64 to Ollama's /api/generate."""
        log = get_logger("ollama-vision", run_id)
        t0 = time.time()
        resp = _post_with_retry(
            get_settings().OLLAMA_URL,
            {
                "model": model,
                "system": system_prompt,
                "prompt": user_prompt,
                "images": [image_data],
                "stream": False,
                "options": {"temperature": temperature},
            },
            get_settings().OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.json().get("response", "").strip()
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
        """Send a chat completion (message list) and return the raw text response."""
        log = get_logger("ollama-chat", run_id)
        t0 = time.time()
        base_url = get_settings().OLLAMA_URL.rsplit("/api/generate", 1)[0]
        chat_url = f"{base_url}/api/chat"
        resp = _post_with_retry(
            chat_url,
            {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
            get_settings().OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.json().get("message", {}).get("content", "").strip()
        log.info("chat ok", model=model, duration_ms=int((time.time() - t0) * 1000))
        return text


_DEFAULT_CLIENT = OllamaInferenceClient()


def complete_json(
    system_prompt: str,
    user_prompt: str,
    model: str,
    *,
    max_reprompts: int = 2,
    temperature: float = 0.1,
    run_id: str | None = None,
) -> dict:
    """Delegates to the default OllamaInferenceClient instance."""
    return _DEFAULT_CLIENT.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        max_reprompts=max_reprompts,
        temperature=temperature,
        run_id=run_id,
    )


def complete_code(
    system_prompt: str,
    user_prompt: str,
    model: str,
    *,
    max_reprompts: int = 2,
    temperature: float = 0.1,
    run_id: str | None = None,
) -> str:
    """Delegates to the default OllamaInferenceClient instance."""
    return _DEFAULT_CLIENT.complete_code(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        max_reprompts=max_reprompts,
        temperature=temperature,
        run_id=run_id,
    )
