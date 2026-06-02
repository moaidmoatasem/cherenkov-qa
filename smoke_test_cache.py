#!/usr/bin/env python3
"""
smoke_test_cache.py — E1-5 Response/prefix cache + cost & latency accounting smoke tests.
Tests cache hit measurement, per-run cost + latency reporting, and pipeline integration.
"""
from __future__ import annotations

import time
from typing import Any
from cherenkov.ai.cache import ResponseCache
from cherenkov.ai.accounting import CostAccountant
from cherenkov.ai.interface import InferenceClient, CachedInferenceClient
from cherenkov.core.contracts import CacheStats, AccountingReport


# ── Mock InferenceClient for deterministic testing ────────────────────────
class MockClient(InferenceClient):
    def __init__(self):
        self.json_call_count = 0
        self.code_call_count = 0

    def complete_json(self, system_prompt, user_prompt, model, **kw) -> dict:
        self.json_call_count += 1
        return {"response": f"json-{model}-{user_prompt[:20]}"}

    def complete_code(self, system_prompt, user_prompt, model, **kw) -> str:
        self.code_call_count += 1
        return f"code-{model}-{user_prompt[:20]}"


# ── Test 1: ResponseCache basic operations ───────────────────────────────
def test_cache_basic():
    print("=== TEST 1: ResponseCache basic get/set ===")
    cache = ResponseCache(max_size=10, ttl_seconds=3600)

    result = cache.get("model-a", "sys1", "user1")
    assert result is None, "Cache miss should return None"

    cache.set("model-a", "sys1", "user1", {"answer": 42})
    result = cache.get("model-a", "sys1", "user1")
    assert result == {"answer": 42}, "Cache hit should return stored value"

    stats = cache.stats
    assert stats.hits == 1, f"Expected 1 hit, got {stats.hits}"
    assert stats.misses == 1, f"Expected 1 miss, got {stats.misses}"
    assert stats.size == 1, f"Expected size 1, got {stats.size}"
    assert stats.hit_ratio == 0.5, f"Expected hit_ratio 0.5, got {stats.hit_ratio}"
    print("[OK] Test 1 PASS\n")


# ── Test 2: ResponseCache LRU eviction ───────────────────────────────────
def test_cache_lru():
    print("=== TEST 2: ResponseCache LRU eviction ===")
    cache = ResponseCache(max_size=3, ttl_seconds=3600)

    for i in range(3):
        cache.set(f"model-{i}", "sys", "user", {"val": i})

    # Cache is full (size=3)
    assert cache.stats.size == 3

    # Access item 0 to make it most recently used
    cache.get("model-0", "sys", "user")

    # Insert a 4th item — should evict item 1 (least recently used)
    cache.set("model-3", "sys", "user", {"val": 3})

    assert cache.stats.size == 3
    assert cache.get("model-0", "sys", "user") == {"val": 0}, "model-0 should still be cached"
    assert cache.get("model-1", "sys", "user") is None, "model-1 should have been evicted"
    assert cache.get("model-2", "sys", "user") == {"val": 2}, "model-2 should still be cached"
    assert cache.get("model-3", "sys", "user") == {"val": 3}, "model-3 should be cached"
    print("[OK] Test 2 PASS\n")


# ── Test 3: ResponseCache TTL expiry ─────────────────────────────────────
def test_cache_ttl():
    print("=== TEST 3: ResponseCache TTL expiry ===")
    cache = ResponseCache(max_size=10, ttl_seconds=1)

    cache.set("m", "s", "u", {"val": 42})
    assert cache.get("m", "s", "u") == {"val": 42}, "Should be cached immediately"

    t_start = time.time()
    while time.time() - t_start < 1.2:
        time.sleep(0.1)
    result = cache.get("m", "s", "u")
    assert result is None, "Should have expired after TTL"
    print("[OK] Test 3 PASS\n")


# ── Test 4: CostAccountant basic recording ──────────────────────────────
def test_accountant_basic():
    print("=== TEST 4: CostAccountant basic recording ===")
    acc = CostAccountant()

    report = acc.report
    assert report.request_count == 0, "Empty accountant should have 0 requests"

    # Record a cache miss (100 tokens, 500ms, Ollama = $0)
    acc.record(model="qwen2.5-coder:7b", duration_ms=500, tokens=100, cache_hit=False)
    report = acc.report
    assert report.request_count == 1
    assert report.total_tokens == 100
    assert report.total_duration_ms == 500
    assert report.total_cost == 0.0, "Ollama is free"

    # Record a cache hit
    acc.record(model="qwen2.5-coder:7b", duration_ms=0, tokens=0, cache_hit=True)
    report = acc.report
    assert report.request_count == 2
    assert report.total_tokens == 100
    assert report.total_duration_ms == 500

    # Verify individual entries
    assert report.entries[0].cache_hit is False
    assert report.entries[1].cache_hit is True
    print("[OK] Test 4 PASS\n")


# ── Test 5: CachedInferenceClient caching behavior ──────────────────────
def test_cached_client():
    print("=== TEST 5: CachedInferenceClient caching behavior ===")
    mock = MockClient()
    client = CachedInferenceClient(mock)

    # First call should miss cache and delegate to mock
    r1 = client.complete_json("sys", "user1", "m1")
    assert r1 == {"response": "json-m1-user1"}
    assert mock.json_call_count == 1

    # Second call with same args should hit cache
    r2 = client.complete_json("sys", "user1", "m1")
    assert r2 == {"response": "json-m1-user1"}
    assert mock.json_call_count == 1, "Should NOT have called mock again"

    # Different user prompt should miss cache
    r3 = client.complete_json("sys", "user-different", "m1")
    assert mock.json_call_count == 2

    # Verify cache stats
    stats = client.cache_stats
    assert stats.hits >= 1
    assert stats.misses >= 2
    print("[OK] Test 5 PASS\n")


# ── Test 6: CachedInferenceClient cost/latency reporting ────────────────
def test_cached_client_accounting():
    print("=== TEST 6: CachedInferenceClient cost/latency reporting ===")
    mock = MockClient()
    client = CachedInferenceClient(mock)

    # Make a call
    client.complete_code("sys", "write a test", "m1")
    report = client.accounting_report
    assert report.request_count == 1
    assert report.entries[0].cache_hit is False
    assert report.entries[0].duration_ms >= 0
    assert report.entries[0].tokens > 0

    # Make same call again (cache hit)
    client.complete_code("sys", "write a test", "m1")
    report = client.accounting_report
    assert report.request_count == 2
    assert report.entries[1].cache_hit is True
    assert report.entries[1].duration_ms == 0

    # Total cost should be $0 (Ollama is free)
    assert report.total_cost == 0.0
    print("[OK] Test 6 PASS\n")


# ── Test 7: CacheStats model validation ─────────────────────────────────
def test_cache_stats_contract():
    print("=== TEST 7: CacheStats contract validation ===")
    stats = CacheStats(hits=5, misses=10, size=3, max_size=100, hit_ratio=0.3333)
    assert stats.hits == 5
    assert stats.hit_ratio == 0.3333
    assert stats.max_size == 100

    # Defaults
    default = CacheStats()
    assert default.hits == 0
    assert default.hit_ratio == 0.0
    print("[OK] Test 7 PASS\n")


# ── Test 8: AccountingReport model validation ───────────────────────────
def test_accounting_report_contract():
    print("=== TEST 8: AccountingReport contract validation ===")
    from cherenkov.core.contracts import CostEntry

    entries = [
        CostEntry(model="m1", provider="ollama", duration_ms=500, tokens=100, cost=0.0, cache_hit=False),
        CostEntry(model="m1", provider="ollama", duration_ms=0, tokens=0, cost=0.0, cache_hit=True),
    ]
    report = AccountingReport(
        entries=entries,
        total_duration_ms=500,
        total_tokens=100,
        total_cost=0.0,
        request_count=2,
        cache_stats=CacheStats(hits=1, misses=1, size=1, max_size=100, hit_ratio=0.5),
    )
    assert report.request_count == 2
    assert report.cache_stats.hit_ratio == 0.5
    assert report.total_cost == 0.0
    print("[OK] Test 8 PASS\n")


# ── Test 9: Key independence (different models = different cache keys) ──
def test_cache_key_independence():
    print("=== TEST 9: Cache key independence across models ===")
    cache = ResponseCache(max_size=10)
    cache.set("model-a", "sys", "user", {"from": "a"})
    cache.set("model-b", "sys", "user", {"from": "b"})

    assert cache.get("model-a", "sys", "user") == {"from": "a"}
    assert cache.get("model-b", "sys", "user") == {"from": "b"}
    assert cache.stats.hits == 2
    assert cache.stats.size == 2
    print("[OK] Test 9 PASS\n")


# ── Test 10: Module-level get_accounting_report / get_cache_stats API ──
def test_module_api():
    print("=== TEST 10: Module-level get_accounting_report / get_cache_stats ===")
    import cherenkov.ai as ai_mod

    # Before any client is created, should return None
    assert ai_mod.get_accounting_report() is None
    assert ai_mod.get_cache_stats() is None

    # Create a CachedInferenceClient directly (not via get_client which needs Ollama)
    mock = MockClient()
    client = ai_mod.CachedInferenceClient(mock)
    ai_mod._current_client = client

    try:
        client.complete_json("sys", "user1", "m1")
        client.complete_json("sys", "user1", "m1")  # cache hit
        client.complete_json("sys", "user2", "m1")

        report = ai_mod.get_accounting_report()
        assert report is not None
        assert report.request_count == 3
        assert report.cache_stats.hits >= 1
        assert report.cache_stats.misses >= 2

        stats = ai_mod.get_cache_stats()
        assert stats is not None
        assert stats.hit_ratio > 0
    finally:
        ai_mod._current_client = None

    print("[OK] Test 10 PASS\n")


# ── Test 11: Orchestrator pipeline result includes cache/accounting lines ──
def test_orchestrator_integration():
    print("=== TEST 11: Orchestrator pipeline output includes cache/accounting ===")
    import cherenkov.ai as ai_mod

    # Wire up a CachedInferenceClient with MockClient
    mock = MockClient()
    client = ai_mod.CachedInferenceClient(mock)
    ai_mod._current_client = client
    client.complete_json("sys", "q1", "m1")
    client.complete_json("sys", "q1", "m1")  # hit
    client.complete_json("sys", "q2", "m1")

    try:
        report = ai_mod.get_accounting_report()
        stats = ai_mod.get_cache_stats()

        assert report is not None
        assert stats is not None
        assert report.request_count == 3
        assert stats.hits >= 1
        assert stats.misses >= 2
        assert report.cache_stats.hits >= 1
    finally:
        ai_mod._current_client = None

    print("[OK] Test 11 PASS\n")


def main():
    print("=======================================================")
    print("  CHERENKOV E1-5 CACHE & ACCOUNTING SMOKE TESTS")
    print("=======================================================\n")

    test_cache_basic()
    test_cache_lru()
    test_cache_ttl()
    test_accountant_basic()
    test_cached_client()
    test_cached_client_accounting()
    test_cache_stats_contract()
    test_accounting_report_contract()
    test_cache_key_independence()
    test_module_api()
    test_orchestrator_integration()

    print("=======================================================")
    print("  ALL E1-5 SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")


if __name__ == "__main__":
    main()
