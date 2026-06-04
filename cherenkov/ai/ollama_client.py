"""
CHERENKOV ai/ollama_client.py — the single doorway to local models.
Authority: v3.1 + delta.

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
from typing import Protocol

import requests

from cherenkov.core.errors import OllamaJSONError, get_logger
from cherenkov.core.config import Config
from cherenkov.ai.interface import InferenceClient


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
            run_id=run_id
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
        return complete_code(
            system_prompt,
            user_prompt,
            model,
            temperature=temperature,
            run_id=run_id
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
            messages=messages,
            model=model,
            temperature=temperature,
            run_id=run_id
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


def _json_repair(text: str) -> dict | None:
    """Last-ditch before reprompting: grab the outermost {...} and retry."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return _try_json(m.group(0)) if m else None


class OllamaInferenceClient(InferenceClient):
    """Ollama-specific implementation of the InferenceClient interface."""

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

        while attempt <= max_reprompts:
            t0 = time.time()
            resp = requests.post(
                Config.OLLAMA_URL,
                json={
                    "model": model,
                    "system": system_prompt,     # static -> cached prefix
                    "prompt": user_prompt,
                    "format": "json",            # constrain sampling to valid JSON (D-9)
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                timeout=Config.OLLAMA_TIMEOUT,
            )
            resp.raise_for_status()
            last_raw = resp.json().get("response", "")
            dt_ms = int((time.time() - t0) * 1000)

            parsed = _try_json(last_raw) or _json_repair(last_raw)
            if parsed is not None:
                log.info("json ok", model=model, attempt=attempt, duration_ms=dt_ms)
                return parsed

            attempt += 1
            log.warning("json invalid, reprompting", model=model, attempt=attempt,
                        duration_ms=dt_ms)

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
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        """For the GENERATE stage: we want raw TS code, not JSON. Same static-prompt
        discipline for prefix caching. Strips stray markdown fences."""
        log = get_logger("ollama", run_id)
        t0 = time.time()
        resp = requests.post(
            Config.OLLAMA_URL,
            json={
                "model": model,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=Config.OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.json().get("response", "").strip()
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
        """Vision request: send image as base64 to Ollama's /api/generate."""
        log = get_logger("ollama-vision", run_id)
        t0 = time.time()
        resp = requests.post(
            Config.OLLAMA_URL,
            json={
                "model": model,
                "system": system_prompt,
                "prompt": user_prompt,
                "images": [image_data],
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=Config.OLLAMA_TIMEOUT,
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
        base_url = Config.OLLAMA_URL.rsplit("/api/generate", 1)[0]
        chat_url = f"{base_url}/api/chat"
        resp = requests.post(
            chat_url,
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=Config.OLLAMA_TIMEOUT,
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
    temperature: float = 0.1,
    run_id: str | None = None,
) -> str:
    """Delegates to the default OllamaInferenceClient instance."""
    return _DEFAULT_CLIENT.complete_code(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        run_id=run_id,
    )

