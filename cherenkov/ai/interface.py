"""
CHERENKOV ai/interface.py — model-agnostic inference client seam.
Authority: v3.1 + delta.
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


class CachedInferenceClient(InferenceClient):
    """Transparent wrapper that adds response caching + cost/latency accounting
    to any InferenceClient.

    Checks the cache before delegating to the underlying client. On a cache hit
    returns instantly (0ms effective latency, $0 cost). Tracks every request in
    the CostAccountant for per-run reporting.
    """

    def __init__(
        self,
        client: InferenceClient,
        cache: ResponseCache | None = None,
        accountant: CostAccountant | None = None,
    ):
        self._client = client
        self._cache = cache or ResponseCache()
        self._accountant = accountant or CostAccountant()

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
        cached = self._cache.get(model, system_prompt, user_prompt)
        if cached is not None:
            self._accountant.record(model=model, duration_ms=0, tokens=0, cache_hit=True)
            return cached

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

        self._cache.set(model, system_prompt, user_prompt, result)
        self._accountant.record_json(model=model, duration_ms=dt_ms, output=result, cache_hit=False)

        return result

    def complete_code(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        cached = self._cache.get(model, system_prompt, user_prompt)
        if cached is not None:
            self._accountant.record(model=model, duration_ms=0, tokens=0, cache_hit=True)
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

        self._cache.set(model, system_prompt, user_prompt, result)
        self._accountant.record_code(model=model, duration_ms=dt_ms, output=result, cache_hit=False)

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

    def chat(
        self,
        messages: list[dict],
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        return self._client.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            run_id=run_id,
        )
