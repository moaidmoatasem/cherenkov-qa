"""Unit tests for cherenkov/core/orchestrator.py — CircuitBreaker, event callback, stage wiring."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch, call

import pytest


# ── CircuitBreaker ──────────────────────────────────────────────────────────

class TestCircuitBreaker:
    def _make(self, threshold=2):
        from cherenkov.core.orchestrator import CircuitBreaker
        return CircuitBreaker(threshold=threshold)

    def test_initial_state_closed(self):
        cb = self._make()
        assert not cb.tripped

    def test_trips_after_threshold(self):
        cb = self._make(threshold=2)
        cb.record_failure()
        assert not cb.tripped
        cb.record_failure()
        assert cb.tripped

    def test_reset_closes_breaker(self):
        cb = self._make(threshold=1)
        cb.record_failure()
        assert cb.tripped
        cb.reset()
        assert not cb.tripped

    def test_threshold_one(self):
        cb = self._make(threshold=1)
        cb.record_failure()
        assert cb.tripped

    def test_multiple_resets_idempotent(self):
        cb = self._make(threshold=1)
        cb.record_failure()
        cb.reset()
        cb.reset()
        assert not cb.tripped


# ── OrchestrationEngine lifecycle ─────────────────────────────────────────

class TestOrchestratorLifecycle:
    def _make(self, **kwargs):
        from cherenkov.core.orchestrator import OrchestrationEngine
        with tempfile.TemporaryDirectory() as d:
            with patch("os.makedirs"), patch("builtins.open", MagicMock()), \
                 patch("cherenkov.core.orchestrator.set_events_file"):
                orch = OrchestrationEngine(run_id="test-orch", **kwargs)
                orch._events_file = MagicMock()
                return orch

    def test_run_id_assigned(self):
        orch = self._make()
        assert orch.run_id == "test-orch"

    def test_auto_run_id_generated_if_none(self):
        with patch("os.makedirs"), patch("builtins.open", MagicMock()), \
             patch("cherenkov.core.orchestrator.set_events_file"):
            from cherenkov.core.orchestrator import OrchestrationEngine
            orch = OrchestrationEngine()
            orch._events_file = MagicMock()
            assert orch.run_id
            assert len(orch.run_id) == 8

    def test_close_releases_file(self):
        orch = self._make()
        mock_file = MagicMock()
        mock_file.closed = False
        orch._events_file = mock_file
        with patch("cherenkov.core.orchestrator.set_events_file"):
            orch.close()
        mock_file.close.assert_called_once()

    def test_close_idempotent_if_already_closed(self):
        orch = self._make()
        mock_file = MagicMock()
        mock_file.closed = True
        orch._events_file = mock_file
        with patch("cherenkov.core.orchestrator.set_events_file"):
            orch.close()
        mock_file.close.assert_not_called()


# ── Event callback ───────────────────────────────────────────────────────────

class TestEventCallback:
    def _make_with_callback(self, cb):
        with patch("os.makedirs"), patch("builtins.open", MagicMock()), \
             patch("cherenkov.core.orchestrator.set_events_file"):
            from cherenkov.core.orchestrator import OrchestrationEngine
            orch = OrchestrationEngine(run_id="cb-test", event_callback=cb)
            orch._events_file = MagicMock()
            return orch

    def test_callback_invoked_with_event_and_data(self):
        events = []
        orch = self._make_with_callback(lambda e, d: events.append((e, d)))
        orch._emit_event("stage_start", {"stage": "INGEST"})
        assert events == [("stage_start", {"stage": "INGEST"})]

    def test_callback_error_does_not_propagate(self):
        def bad_cb(e, d):
            raise RuntimeError("callback exploded")

        orch = self._make_with_callback(bad_cb)
        orch._emit_event("any", {})  # should not raise

    def test_no_callback_is_noop(self):
        orch = self._make_with_callback(None)
        orch._emit_event("any", {})  # should not raise

    def test_callback_receives_multiple_events(self):
        events = []
        orch = self._make_with_callback(lambda e, d: events.append(e))
        for name in ("start", "progress", "done"):
            orch._emit_event(name, {})
        assert events == ["start", "progress", "done"]


# ── run_ingest simulation guard ─────────────────────────────────────────────

class TestRunIngestSimulationGuard:
    def _make(self):
        with patch("os.makedirs"), patch("builtins.open", MagicMock()), \
             patch("cherenkov.core.orchestrator.set_events_file"):
            from cherenkov.core.orchestrator import OrchestrationEngine
            orch = OrchestrationEngine(run_id="sim-test")
            orch._events_file = MagicMock()
            return orch

    def test_simulate_malformed_blocked_in_production(self):
        orch = self._make()
        with patch.dict(os.environ, {"CHERENKOV_ENV": "production"}):
            with pytest.raises(RuntimeError):
                orch.run_ingest("dummy.yaml", simulate_malformed=True)

    def test_simulate_malformed_allowed_in_development(self):
        orch = self._make()
        with patch.dict(os.environ, {"CHERENKOV_ENV": "development"}):
            result = orch.run_ingest("dummy.yaml", simulate_malformed=True)
        # Returns a bare dict (intentional bad output for mutation testing)
        assert isinstance(result, dict)
        assert "endpoints" in result

    def test_simulate_plan_blocked_in_production(self):
        from cherenkov.core.contracts import IngestOutput, Status
        orch = self._make()
        dummy_ingest = MagicMock(spec=IngestOutput)
        dummy_ingest.endpoints = []
        with patch.dict(os.environ, {"CHERENKOV_ENV": "production"}):
            with pytest.raises(RuntimeError):
                orch.run_plan(dummy_ingest, simulate_malformed=True)
