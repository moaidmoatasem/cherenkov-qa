"""Unit tests for OrchestrationEngine._execute_stage_with_retry and CircuitBreaker integration."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch, call

import pytest

from cherenkov.core.errors import ContractError
from cherenkov.core.orchestrator import CircuitBreaker, OrchestrationEngine
from cherenkov.core.contracts import (
    IngestOutput, Status, StageMeta, StageError,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_engine():
    """Return an OrchestrationEngine with all I/O mocked out."""
    with patch("os.makedirs"), \
         patch("builtins.open", MagicMock()), \
         patch("cherenkov.core.orchestrator.set_events_file"):
        eng = OrchestrationEngine(run_id="retry-test", error_threshold=2)
        eng._events_file = MagicMock()
        return eng


def _good_ingest() -> IngestOutput:
    return IngestOutput(
        endpoints=[],
        client_stub_path="stub/client.ts",
        status=Status.OK,
        errors=[],
        metadata=StageMeta(stage="INGEST", duration_ms=10),
    )


def _fallback_ingest() -> IngestOutput:
    return IngestOutput(
        endpoints=[],
        client_stub_path="",
        status=Status.FAILED,
        errors=[StageError(code="FALLBACK", detail="fallback")],
        metadata=StageMeta(stage="INGEST", duration_ms=0),
    )


# ── _execute_stage_with_retry ────────────────────────────────────────────────

class TestExecuteStageWithRetry:
    def test_success_on_first_attempt(self):
        eng = _make_engine()
        result = eng._execute_stage_with_retry(
            "INGEST",
            stage_func=_good_ingest,
            fallback_factory=_fallback_ingest,
        )
        assert result.status == Status.OK

    def test_returns_fallback_after_all_retries_fail(self):
        eng = _make_engine()
        always_bad = lambda: (_ for _ in ()).throw(ContractError("bad"))
        # ContractError on every attempt -> exhausts 3 attempts -> fallback
        with patch("time.sleep"):  # skip backoff delays
            result = eng._execute_stage_with_retry(
                "INGEST",
                stage_func=lambda: (_ for _ in ()).throw(ContractError("bad")),
                fallback_factory=_fallback_ingest,
            )
        assert result.status == Status.FAILED
        assert result.errors[0].code == "FALLBACK"

    def test_circuit_breaker_tripped_after_fallback(self):
        eng = _make_engine()
        with patch("time.sleep"):
            eng._execute_stage_with_retry(
                "INGEST",
                stage_func=lambda: (_ for _ in ()).throw(ContractError("x")),
                fallback_factory=_fallback_ingest,
            )
        # threshold=2, one fallback = error_count=1 (not yet tripped)
        assert eng.breaker.error_count == 1

    def test_circuit_breaker_trips_after_two_fallbacks(self):
        eng = _make_engine()
        with patch("time.sleep"):
            for _ in range(2):
                eng._execute_stage_with_retry(
                    "INGEST",
                    stage_func=lambda: (_ for _ in ()).throw(ContractError("x")),
                    fallback_factory=_fallback_ingest,
                )
        assert eng.breaker.tripped

    def test_raw_dict_result_triggers_contract_error_and_fallback(self):
        """Stage returning a raw dict (not a Pydantic model) triggers ContractError."""
        eng = _make_engine()
        with patch("time.sleep"):
            result = eng._execute_stage_with_retry(
                "INGEST",
                stage_func=lambda: {"endpoints": [], "client_stub_path": ""},
                fallback_factory=_fallback_ingest,
            )
        assert result.status == Status.FAILED

    def test_success_on_second_attempt(self):
        eng = _make_engine()
        call_count = {"n": 0}

        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise ContractError("first attempt fails")
            return _good_ingest()

        with patch("time.sleep"):
            result = eng._execute_stage_with_retry(
                "INGEST",
                stage_func=flaky,
                fallback_factory=_fallback_ingest,
            )
        assert result.status == Status.OK
        assert call_count["n"] == 2

    def test_breaker_not_tripped_on_eventual_success(self):
        eng = _make_engine()
        call_count = {"n": 0}

        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise ContractError("first attempt fails")
            return _good_ingest()

        with patch("time.sleep"):
            eng._execute_stage_with_retry("INGEST", flaky, _fallback_ingest)
        assert not eng.breaker.tripped
        assert eng.breaker.error_count == 0


# ── CircuitBreaker thread safety ─────────────────────────────────────────────

class TestCircuitBreakerThreadSafety:
    def test_concurrent_failures_trip_correctly(self):
        import threading
        cb = CircuitBreaker(threshold=10)
        threads = [threading.Thread(target=cb.record_failure) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert cb.tripped
        assert cb.error_count == 10

    def test_reset_under_concurrent_reads(self):
        import threading
        cb = CircuitBreaker(threshold=1)
        cb.record_failure()
        results = []

        def read():
            results.append(cb.tripped)

        threads = [threading.Thread(target=read) for _ in range(20)]
        reset_thread = threading.Thread(target=cb.reset)
        for t in threads:
            t.start()
        reset_thread.start()
        for t in threads:
            t.join()
        reset_thread.join()
        # After reset, must be False regardless of read timing
        assert not cb.tripped
