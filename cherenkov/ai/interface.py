"""
CHERENKOV ai/interface.py — model-agnostic inference client seam.
"""

from __future__ import annotations

import abc
import time

from cherenkov.core.contracts import CacheStats, AccountingReport
from cherenkov.ai.cache import ResponseCache
from cherenkov.ai.accounting import CostAccountant


class InferenceClient(abc.ABC):
    """Abstract base class representing an inference capability seam.

    This is the core seam that Epoch 1 (Substrate Router) will build upon.
    """

    @abc.abstractmethod
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
        """Return a parsed JSON object from the model, or raise OllamaJSONError."""
        pass

    @abc.abstractmethod
    def complete_code(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        """For the GENERATE stage: we want raw TS code, not JSON."""
        pass

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
        """Vision-Language: send an image and get a text description.

        `image_data` is a base64-encoded image string (no data URI prefix).
        Default implementation raises NotImplementedError.
        """
        raise NotImplementedError("Vision not supported by this provider")


class CachedInferenceClient(InferenceClient):
    """Transparent wrapper that adds response caching + cost/latency accounting
    to any InferenceClient.

    Checks the cache before delegating to the underlying client. On a cache hit
    returns instantly (0ms effective latency, $0 cost). Tracks every request in
    the CostAccountant for per-run reporting, using real token counts from the
    underlying client's _token_usage attribute when available.
    """

    def __init__(
        self,
        client: InferenceClient,
        cache: ResponseCache | None = None,
        accountant: CostAccountant | None = None,
        provider: str = "ollama",
    ):
        self._client = client
        self._cache = cache or ResponseCache()
        self._accountant = accountant or CostAccountant()
        self._provider = provider

    def _real_token_usage(self) -> dict[str, int]:
        """Read token counts the underlying client captured from the API response."""
        return getattr(
            self._client,
            "_token_usage",
            {"prompt_tokens": 0, "completion_tokens": 0, "reprompts": 0},
        )

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        max_reprompts: int = 2,
        temperature: float = 0.1,
        run_id: str | None = None,
        stage: str = "",
    ) -> dict:
        cached = self._cache.get(model, system_prompt, user_prompt)
        if cached is not None:
            self._accountant.record(
                model=model,
                duration_ms=0,
                tokens=0,
                cache_hit=True,
                provider=self._provider,
                stage=stage,
                run_id=run_id or "",
            )
            return cached  # type: ignore

        t0 = time.time()
        result = self._client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_reprompts=max_reprompts,
            temperature=temperature,
            run_id=run_id,
        )
        dt_ms = int((time.time() - t0) * 1000)
        usage = self._real_token_usage()

        self._cache.set(model, system_prompt, user_prompt, result)
        self._accountant.record_json(
            model=model,
            duration_ms=dt_ms,
            output=result,
            cache_hit=False,
            provider=self._provider,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            stage=stage,
            run_id=run_id or "",
            reprompts=usage.get("reprompts", 0),
        )

        return result

    def complete_code(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
        stage: str = "",
    ) -> str:
        cached = self._cache.get(model, system_prompt, user_prompt)
        if cached is not None:
            self._accountant.record(
                model=model,
                duration_ms=0,
                tokens=0,
                cache_hit=True,
                provider=self._provider,
                stage=stage,
                run_id=run_id or "",
            )
            return str(cached)

        t0 = time.time()
        result = self._client.complete_code(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            run_id=run_id,
        )
        dt_ms = int((time.time() - t0) * 1000)
        usage = self._real_token_usage()

        self._cache.set(model, system_prompt, user_prompt, result)
        self._accountant.record_code(
            model=model,
            duration_ms=dt_ms,
            output=result,
            cache_hit=False,
            provider=self._provider,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            stage=stage,
            run_id=run_id or "",
            reprompts=usage.get("reprompts", 0),
        )

        return result

    @property
    def cache_stats(self) -> CacheStats:
        return self._cache.stats

    @property
    def accounting_report(self) -> AccountingReport:
        rep = self._accountant.report
        rep.cache_stats = self._cache.stats
        return rep

    @property
    def wrapped_client(self) -> InferenceClient:
        return self._client

    def complete_vision(
        self,
        system_prompt: str,
        user_prompt: str,
        image_data: str,
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
        stage: str = "VISION",
    ) -> str:
        cached = self._cache.get(model, system_prompt, user_prompt + image_data[:80])
        if cached is not None:
            self._accountant.record(
                model=model,
                duration_ms=0,
                tokens=0,
                cache_hit=True,
                provider=self._provider,
                stage=stage,
                run_id=run_id or "",
            )
            return str(cached)

        t0 = time.time()
        result = self._client.complete_vision(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            image_data=image_data,
            model=model,
            temperature=temperature,
            run_id=run_id,
        )
        dt_ms = int((time.time() - t0) * 1000)
        usage = self._real_token_usage()

        self._cache.set(model, system_prompt, user_prompt + image_data[:80], result)
        self._accountant.record_code(
            model=model,
            duration_ms=dt_ms,
            output=result,
            cache_hit=False,
            provider=self._provider,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            stage=stage,
            run_id=run_id or "",
        )

        return result

    def chat(
        self,
        messages: list[dict],
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        return self._client.chat(  # type: ignore
            messages=messages,
            model=model,
            temperature=temperature,
            run_id=run_id,
        )
