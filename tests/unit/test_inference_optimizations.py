"""Tests for LLM inference optimizations: substrate response caching and
bounded-concurrency certification (see cherenkov/substrate/provider.py and
cherenkov/substrate/certification.py).
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

from cherenkov.substrate import provider_base
from cherenkov.core.contracts import ReasoningRequest
from cherenkov.core.settings import get_settings
from cherenkov.substrate.certification import ModelCertificationManager
from cherenkov.substrate.provider import OllamaProvider


def _reset_shared_cache() -> None:
    provider_base._SHARED_RESPONSE_CACHE = None


def test_provider_reuses_cached_response_for_identical_request():
    _reset_shared_cache()
    mock_client = MagicMock()
    mock_client.complete_code.return_value = "hello world"

    prov = OllamaProvider()
    prov.client = provider_base.wrap_with_cache(mock_client, "ollama")

    req = ReasoningRequest(task="same prompt", capability_tier="small")
    first = prov.generate(req)
    second = prov.generate(req)

    assert first.cached is False
    assert second.cached is True
    assert second.content == first.content
    assert mock_client.complete_code.call_count == 1


def test_provider_cache_disabled_falls_back_to_raw_client():
    _reset_shared_cache()
    settings = get_settings()
    old = settings.CACHE_ENABLED
    settings.CACHE_ENABLED = False
    try:
        mock_client = MagicMock()
        mock_client.complete_code.return_value = "hello world"
        wrapped = provider_base.wrap_with_cache(mock_client, "ollama")
        assert wrapped is mock_client

        prov = OllamaProvider()
        prov.client = wrapped
        req = ReasoningRequest(task="same prompt", capability_tier="small")
        prov.generate(req)
        prov.generate(req)
        assert mock_client.complete_code.call_count == 2
    finally:
        settings.CACHE_ENABLED = old
        _reset_shared_cache()


class _ConcurrencyTrackingProvider:
    """Records the peak number of simultaneously in-flight generate() calls."""

    def __init__(self, delay: float = 0.02):
        self.delay = delay
        self._lock = threading.Lock()
        self._inflight = 0
        self.peak_inflight = 0

    def generate(self, request: ReasoningRequest):
        from cherenkov.core.contracts import ReasoningResult

        with self._lock:
            self._inflight += 1
            self.peak_inflight = max(self.peak_inflight, self._inflight)
        time.sleep(self.delay)
        with self._lock:
            self._inflight -= 1
        return ReasoningResult(content="CHERENKOV", provider="dummy", model="dummy-model")

    def capabilities(self):
        from cherenkov.substrate.provider import ProviderCapabilities

        return ProviderCapabilities(
            capability_tiers=["small"], requires_egress=False, provider_name="dummy"
        )


def test_certify_tier_runs_gold_set_items_concurrently(tmp_path):
    import json

    gold_set_file = tmp_path / "gold_set.json"
    items = [
        {"prompt": f"Say CHERENKOV #{i}.", "expected_contains": ["CHERENKOV"]}
        for i in range(6)
    ]
    gold_set_file.write_text(json.dumps({"items": items}), encoding="utf-8")

    settings = get_settings()
    old_path = settings.CERTIFICATION_GOLD_SET_PATH
    old_concurrency = settings.CERTIFICATION_MAX_CONCURRENCY
    settings.CERTIFICATION_GOLD_SET_PATH = str(gold_set_file)
    settings.CERTIFICATION_MAX_CONCURRENCY = 3

    try:
        manager = ModelCertificationManager()
        prov = _ConcurrencyTrackingProvider()
        result = manager.certify_tier("small", prov)

        assert result.certified is True
        # sequential execution would never exceed 1 in-flight call at a time
        assert prov.peak_inflight > 1
        assert prov.peak_inflight <= settings.CERTIFICATION_MAX_CONCURRENCY
    finally:
        settings.CERTIFICATION_GOLD_SET_PATH = old_path
        settings.CERTIFICATION_MAX_CONCURRENCY = old_concurrency
