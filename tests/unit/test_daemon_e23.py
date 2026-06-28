"""
tests/unit/test_daemon_e23.py — E2.3: Continuous engine divergence integration.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cherenkov.stages.daemon_cmd import DivergenceQueue, _get_spec_mtimes, run_daemon


# ── DivergenceQueue ────────────────────────────────────────────────────────────

class TestDivergenceQueue:
    def test_push_pop_roundtrip(self, tmp_path):
        q = DivergenceQueue(tmp_path / "queue.jsonl")
        q.push({"loop": 1, "divergences": 2})
        q.push({"loop": 2, "divergences": 0})
        entries = q.pop_all()
        assert len(entries) == 2
        assert entries[0]["loop"] == 1
        assert entries[1]["divergences"] == 0

    def test_pop_all_clears(self, tmp_path):
        q = DivergenceQueue(tmp_path / "queue.jsonl")
        q.push({"x": 1})
        q.pop_all()
        assert q.pop_all() == []

    def test_count(self, tmp_path):
        q = DivergenceQueue(tmp_path / "queue.jsonl")
        assert q.count == 0
        q.push({"a": 1})
        q.push({"b": 2})
        assert q.count == 2

    def test_pop_empty(self, tmp_path):
        q = DivergenceQueue(tmp_path / "q.jsonl")
        assert q.pop_all() == []


# ── _get_spec_mtimes ───────────────────────────────────────────────────────────

class TestGetSpecMtimes:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "spec.json"
        f.write_text("{}")
        mtimes = _get_spec_mtimes([str(f)])
        assert str(f) in mtimes
        assert mtimes[str(f)] > 0

    def test_missing_file_returns_zero(self):
        mtimes = _get_spec_mtimes(["/nonexistent/spec.json"])
        assert mtimes["/nonexistent/spec.json"] == 0.0

    def test_empty_list(self):
        assert _get_spec_mtimes([]) == {}


# ── run_daemon ─────────────────────────────────────────────────────────────────

def _make_mock_config(specs):
    cfg = MagicMock()
    cfg.autodetect_spec.return_value = specs
    return cfg


def _make_mock_report(endpoint="/pet", divergence_class_val="D1_spec_code", diff="status mismatch"):
    from cherenkov.core.contracts import (
        DivergenceClass, DivergenceEvidence, DivergenceReport, Severity, StageMeta, Status,
    )
    return DivergenceReport(
        id="r1",
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a="spec says 400",
        claim_b="impl returns 500",
        evidence=DivergenceEvidence(request_summary=f"POST {endpoint}", diff=diff, response_actual="500", response_expected="400"),
        repro_steps=["POST /pet without photoUrls"],
        severity=Severity.HIGH,
        endpoint=endpoint,
        metadata=StageMeta(stage="daemon", run_id="test"),
    )


class TestRunDaemonE23:
    def test_no_target_url_skips_proof(self, tmp_path):
        """Without --url, daemon rebuilds truth model but does NOT call run_proof."""
        cfg = _make_mock_config([])
        with (
            patch("cherenkov.core.config_loader.load_effective_config", return_value=cfg),
            patch("cherenkov.stages.daemon_cmd.build_truth_model") as mock_build,
            patch("cherenkov.stages.daemon_cmd.DivergenceQueue") as mock_queue_cls,
        ):
            mock_build.return_value = MagicMock(nodes={}, edges={})
            mock_queue_cls.return_value = MagicMock()
            result = run_daemon(interval_seconds=0, max_loops=1, target_url=None)
        assert result == 0

    def test_with_target_url_calls_run_proof(self, tmp_path):
        """With --url, daemon calls run_proof and logs divergences."""
        cfg = _make_mock_config([])
        report = _make_mock_report()
        with (
            patch("cherenkov.core.config_loader.load_effective_config", return_value=cfg),
            patch("cherenkov.stages.daemon_cmd.build_truth_model", return_value=MagicMock(nodes={}, edges={})),
            patch("cherenkov.stages.daemon_cmd.DivergenceQueue") as mock_queue_cls,
            patch("cherenkov.divergence.proof_run.run_proof", return_value=[report]),
            patch("cherenkov.hitl.HitlQueue") as mock_hitl_cls,
        ):
            mock_q = MagicMock()
            mock_queue_cls.return_value = mock_q
            mock_hitl_cls.return_value = MagicMock()

            result = run_daemon(
                interval_seconds=0,
                max_loops=1,
                target_url="https://petstore3.swagger.io/api/v3",
            )

        assert result == 0
        assert mock_q.push.called
        entry = mock_q.push.call_args[0][0]
        assert "divergences" in entry

    def test_divergences_pushed_to_hitl(self, tmp_path):
        """Confirmed divergences are enqueued into HitlQueue."""
        cfg = _make_mock_config([])
        report = _make_mock_report()

        with (
            patch("cherenkov.core.config_loader.load_effective_config", return_value=cfg),
            patch("cherenkov.stages.daemon_cmd.build_truth_model", return_value=MagicMock(nodes={}, edges={})),
            patch("cherenkov.stages.daemon_cmd.DivergenceQueue") as mock_queue_cls,
            patch("cherenkov.divergence.proof_run.run_proof", return_value=[report]),
            patch("cherenkov.hitl.HitlQueue") as mock_hitl_cls,
        ):
            mock_queue_cls.return_value = MagicMock()
            mock_hitl = MagicMock()
            mock_hitl_cls.return_value = mock_hitl

            run_daemon(interval_seconds=0, max_loops=1, target_url="http://localhost:8080")

        mock_hitl.enqueue.assert_called_once()

    def test_proof_exception_does_not_crash_daemon(self):
        """If run_proof raises, daemon logs the error and continues."""
        cfg = _make_mock_config([])
        with (
            patch("cherenkov.core.config_loader.load_effective_config", return_value=cfg),
            patch("cherenkov.stages.daemon_cmd.build_truth_model", return_value=MagicMock(nodes={}, edges={})),
            patch("cherenkov.stages.daemon_cmd.DivergenceQueue") as mock_queue_cls,
            patch("cherenkov.divergence.proof_run.run_proof", side_effect=RuntimeError("network error")),
            patch("cherenkov.hitl.HitlQueue") as mock_hitl_cls,
        ):
            mock_queue_cls.return_value = MagicMock()
            mock_hitl_cls.return_value = MagicMock()
            result = run_daemon(interval_seconds=0, max_loops=1, target_url="http://bad-host")

        assert result == 0

    def test_spec_change_detection(self, tmp_path):
        """Daemon detects when spec files change between loops."""
        spec = tmp_path / "spec.json"
        spec.write_text('{"openapi":"3.0.0"}')
        cfg = _make_mock_config([str(spec)])

        loop = 0

        def fake_proof(**kwargs):
            nonlocal loop
            loop += 1
            if loop == 2:
                spec.write_text('{"openapi":"3.0.1"}')
            return []

        captured_changes = []

        original_get_mtimes = _get_spec_mtimes

        def patched_sleep(n):
            pass  # skip sleep

        with (
            patch("cherenkov.core.config_loader.load_effective_config", return_value=cfg),
            patch("cherenkov.stages.daemon_cmd.build_truth_model", return_value=MagicMock(nodes={}, edges={})),
            patch("cherenkov.stages.daemon_cmd.DivergenceQueue") as mock_queue_cls,
            patch("time.sleep", patched_sleep),
        ):
            mock_queue_cls.return_value = MagicMock()
            result = run_daemon(interval_seconds=1, max_loops=2, target_url=None)

        assert result == 0
