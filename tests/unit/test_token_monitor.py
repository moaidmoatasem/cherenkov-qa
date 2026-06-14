"""Unit tests for cherenkov/observability/token_monitor.py."""

from __future__ import annotations

import time
import pytest

from cherenkov.observability.token_monitor import (
    TokenMonitor,
    TokenRecord,
    compute_cost,
    get_monitor,
    _price_for,
)


# ── compute_cost ──────────────────────────────────────────────────────────────


def test_ollama_is_free():
    assert compute_cost("ollama", "qwen2.5-coder:7b", 1000, 500) == 0.0


def test_openai_mini_pricing():
    # gpt-4o-mini: $0.000150/1K input + $0.000600/1K output
    cost = compute_cost("openai", "gpt-4o-mini", 1000, 500)
    assert abs(cost - (0.000150 + 0.000600 * 0.5)) < 1e-8


def test_anthropic_haiku_pricing():
    cost = compute_cost("anthropic", "claude-haiku-4-5", 2000, 1000)
    # $0.000250/1K input * 2 + $0.001250/1K output * 1
    expected = 0.000250 * 2 + 0.001250 * 1
    assert abs(cost - expected) < 1e-8


def test_unknown_provider_uses_openai_default():
    price = _price_for("unknown_provider", "some-model")
    assert price["input"] > 0  # defaults to something non-zero


# ── TokenMonitor persistence ──────────────────────────────────────────────────


@pytest.fixture
def monitor():
    return TokenMonitor(db_path=":memory:")


def _make_record(**kwargs) -> TokenRecord:
    defaults = dict(
        run_id="run-001",
        model="qwen2.5-coder:7b",
        provider="ollama",
        stage="GENERATE",
        prompt_tokens=400,
        completion_tokens=300,
        total_tokens=700,
        cost_usd=0.0,
        cache_hit=False,
    )
    defaults.update(kwargs)
    return TokenRecord(**defaults)


def test_record_and_retrieve(monitor):
    monitor.record(_make_record())
    report = monitor.get_report(days=7)
    assert report.total_requests == 1
    assert report.total_tokens == 700
    assert report.total_cost_usd == 0.0


def test_multiple_records_aggregate(monitor):
    for i in range(5):
        monitor.record(_make_record(run_id=f"run-{i}", total_tokens=100))
    report = monitor.get_report(days=7)
    assert report.total_requests == 5
    assert report.total_tokens == 500


def test_cache_hit_rate(monitor):
    monitor.record(_make_record(cache_hit=False))
    monitor.record(_make_record(cache_hit=True))
    monitor.record(_make_record(cache_hit=True))
    report = monitor.get_report(days=7)
    assert report.cache_hit_rate == pytest.approx(2 / 3, abs=0.01)


def test_by_provider_breakdown(monitor):
    monitor.record(_make_record(provider="ollama", cost_usd=0.0, total_tokens=100))
    monitor.record(
        _make_record(
            provider="openai", model="gpt-4o-mini", cost_usd=0.0003, total_tokens=50
        )
    )
    report = monitor.get_report(days=7)
    providers = {row["provider"] for row in report.by_provider}
    assert "ollama" in providers
    assert "openai" in providers


def test_by_stage_breakdown(monitor):
    monitor.record(_make_record(stage="PLAN", total_tokens=200))
    monitor.record(_make_record(stage="GENERATE", total_tokens=300))
    monitor.record(_make_record(stage="GENERATE", total_tokens=150))
    report = monitor.get_report(days=7)
    stages = {row["stage"]: row["total_tokens"] for row in report.by_stage}
    assert stages["GENERATE"] == 450
    assert stages["PLAN"] == 200


def test_daily_trend(monitor):
    monitor.record(_make_record(total_tokens=1000))
    report = monitor.get_report(days=7)
    assert len(report.daily_trend) == 1
    today = time.strftime("%Y-%m-%d")
    assert report.daily_trend[0]["date"] == today
    assert report.daily_trend[0]["tokens"] == 1000


def test_empty_report_has_no_data_recommendation(monitor):
    report = monitor.get_report(days=7)
    codes = {r["code"] for r in report.recommendations}
    assert "NO_DATA" in codes


# ── Recommendations ───────────────────────────────────────────────────────────


def test_local_only_recommendation(monitor):
    monitor.record(_make_record(provider="ollama"))
    monitor.record(_make_record(provider="ollama"))
    report = monitor.get_report(days=7)
    codes = {r["code"] for r in report.recommendations}
    assert "LOCAL_ONLY" in codes


def test_cache_underused_recommendation(monitor):
    # All cache misses → hit rate = 0% → should trigger warning
    for _ in range(10):
        monitor.record(_make_record(cache_hit=False))
    report = monitor.get_report(days=7)
    codes = {r["code"] for r in report.recommendations}
    assert "CACHE_UNDERUSED" in codes


def test_high_reprompt_recommendation(monitor):
    # reprompts > 15% of calls
    for _ in range(10):
        monitor.record(_make_record(reprompts=2))
    report = monitor.get_report(days=7)
    codes = {r["code"] for r in report.recommendations}
    assert "HIGH_REPROMPT_RATE" in codes


def test_paid_provider_spend_recommendation(monitor):
    monitor.record(
        _make_record(
            provider="openai",
            model="gpt-4o",
            cost_usd=0.50,
            total_tokens=5000,
        )
    )
    report = monitor.get_report(days=1)
    codes = {r["code"] for r in report.recommendations}
    assert "PAID_PROVIDER_SPEND" in codes


def test_get_dashboard_data_shape(monitor):
    monitor.record(_make_record())
    data = monitor.get_dashboard_data(days=7)
    assert "summary" in data
    assert "by_provider" in data
    assert "by_stage" in data
    assert "daily_trend" in data
    assert "recommendations" in data
    assert data["summary"]["total_requests"] == 1


# ── get_monitor singleton ─────────────────────────────────────────────────────


def test_get_monitor_returns_same_instance():
    m1 = get_monitor()
    m2 = get_monitor()
    assert m1 is m2
