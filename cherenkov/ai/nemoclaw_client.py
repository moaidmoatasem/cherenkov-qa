"""
CHERENKOV ai/nemoclaw_client.py — NVIDIA NemoClaw inference client.

NemoClaw runs Nemotron models locally via the OpenShell runtime, which exposes
an OpenAI-compatible /v1/chat/completions endpoint.  All inference stays on
device (requires_egress=False).  Authentication uses a Bearer token that is
empty by default in development setups.
"""

from __future__ import annotations

import re
import time

import requests

from cherenkov.core.config import Config
from cherenkov.core.errors import ProviderJSONError, get_logger
from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.ollama_client import _try_json, _json_repair, strip_think


class NemoClawInferenceClient(InferenceClient):
    """OpenShell-backed inference client for NVIDIA NemoClaw.

    Communicates with the NemoClaw OpenShell runtime, which provides an
    OpenAI-compatible chat completions API with optional policy enforcement
    (network/filesystem isolation, real-time approval for external access).
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.base_url = (base_url or Config.NEMOCLAW_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else Config.NEMOCLAW_API_KEY
        self.timeout = timeout or Config.NEMOCLAW_TIMEOUT
        self._token_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reprompts": 0,
        }

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
        response_format: dict | None = None,
    ) -> str:
        body: dict = {
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
            headers=self._headers(),
            json=body,
            timeout=self.timeout,
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
        log = get_logger("nemoclaw", run_id)
        attempt = 0
        last_raw = ""
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "reprompts": 0}

        while attempt <= max_reprompts:
            t0 = time.time()
            try:
                last_raw = self._chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
            except requests.RequestException as exc:
                attempt += 1
                if attempt > max_reprompts:
                    raise ProviderJSONError(
                        f"NemoClaw request failed after {max_reprompts} retries: {exc}"
                    ) from exc
                continue

            dt_ms = int((time.time() - t0) * 1000)
            cleaned = strip_think(last_raw)
            parsed = _try_json(cleaned) or _json_repair(cleaned)
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
        log = get_logger("nemoclaw", run_id)
        t0 = time.time()
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "reprompts": 0}

        text = self._chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
        ).strip()
        text = strip_think(text)
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
        log.info(
            "code ok",
            model=model,
            duration_ms=int((time.time() - t0) * 1000),
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
        log = get_logger("nemoclaw-vision", run_id)
        t0 = time.time()
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "reprompts": 0}

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
            headers=self._headers(),
            json=body,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        self._token_usage["prompt_tokens"] = usage.get("prompt_tokens", 0)
        self._token_usage["completion_tokens"] = usage.get("completion_tokens", 0)
        text = data["choices"][0]["message"]["content"].strip()
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
        log = get_logger("nemoclaw-chat", run_id)
        t0 = time.time()
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "reprompts": 0}

        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=body,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        self._token_usage["prompt_tokens"] = usage.get("prompt_tokens", 0)
        self._token_usage["completion_tokens"] = usage.get("completion_tokens", 0)
        text = data["choices"][0]["message"]["content"].strip()
        log.info("chat ok", model=model, duration_ms=int((time.time() - t0) * 1000))
        return text

    def health(self) -> bool:
        """Return True if the NemoClaw OpenShell runtime is reachable."""
        try:
            resp = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=5,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False
