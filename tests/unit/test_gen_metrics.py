"""Unit tests for cherenkov/governance/gen_metrics.py."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cherenkov.governance.gen_metrics import (
    GATE_PASS_THRESHOLD,
    GenMetricsStore,
    RunGenMetrics,
)


# ── RunGenMetrics ─────────────────────────────────────────────────────────────


def test_initial_state():
    m = RunGenMetrics(run_id="r1")
    assert m.total_generated == 0
    assert m.gate_pass_rate == 0.0
    assert m.operation_coverage == 0.0
    assert m.below_threshold is False  # < 3 generated


def test_record_generation_all_pass():
    m = RunGenMetrics(run_id="r1")
    for _ in range(4):
        m.record_generation(all_gates_passed=True)
    assert m.total_generated == 4
    assert m.gate_passed == 4
    assert m.gate_pass_rate == 1.0
    assert m.below_threshold is False


def test_record_generation_some_fail():
    m = RunGenMetrics(run_id="r1")
    m.record_generation(all_gates_passed=True)
    m.record_generation(all_gates_passed=False)
    m.record_generation(all_gates_passed=False)
    m.record_generation(all_gates_passed=False)
    # 1/4 = 25% < 75% threshold
    assert m.gate_pass_rate == pytest.approx(0.25)
    assert m.below_threshold is True


def test_below_threshold_requires_at_least_3():
    m = RunGenMetrics(run_id="r1")
    m.record_generation(all_gates_passed=False)
    m.record_generation(all_gates_passed=False)
    # only 2 generated → not below threshold yet (not enough data)
    assert m.below_threshold is False
    m.record_generation(all_gates_passed=False)
    # now 3 generated, 0% pass rate → below threshold
    assert m.below_threshold is True


def test_record_500_fault():
    m = RunGenMetrics(run_id="r1")
    m.record_generation(all_gates_passed=True, had_500_fault=True)
    m.record_generation(all_gates_passed=True, had_500_fault=False)
    assert m.faults_500 == 1


def test_record_operation_coverage():
    m = RunGenMetrics(run_id="r1")
    m.record_operation(covered=True)
    m.record_operation(covered=True)
    m.record_operation(covered=False)
    assert m.operations_total == 3
    assert m.operations_covered == 2
    assert m.operation_coverage == pytest.approx(2 / 3)


def test_render_includes_threshold_flag():
    m = RunGenMetrics(run_id="r1")
    for _ in range(3):
        m.record_generation(all_gates_passed=False)
    output = m.render()
    assert "BELOW THRESHOLD" in output


def test_render_no_threshold_flag_when_passing():
    m = RunGenMetrics(run_id="r1")
    for _ in range(4):
        m.record_generation(all_gates_passed=True)
    output = m.render()
    assert "BELOW THRESHOLD" not in output


def test_render_format():
    m = RunGenMetrics(run_id="abc")
    m.record_generation(all_gates_passed=True)
    m.record_operation(covered=True)
    text = m.render()
    assert "run=abc" in text
    assert "Gate Pass Rate" in text
    assert "Operation Coverage" in text
    assert "500-Fault" in text


# ── GenMetricsStore ───────────────────────────────────────────────────────────


def _tmp_store() -> GenMetricsStore:
    tmp = tempfile.mkdtemp()
    return GenMetricsStore(db_path=str(Path(tmp) / "gen_metrics.db"))


def test_store_creates_db():
    store = _tmp_store()
    assert Path(store.db_path).exists()


def test_save_and_history():
    store = _tmp_store()
    m = RunGenMetrics(run_id="run-001")
    m.record_generation(all_gates_passed=True)
    m.record_operation(covered=True)
    store.save(m)

    rows = store.history(limit=5)
    assert len(rows) == 1
    assert rows[0]["run_id"] == "run-001"
    assert rows[0]["total_generated"] == 1
    assert rows[0]["gate_passed"] == 1
    assert rows[0]["below_threshold"] == 0


def test_save_records_below_threshold_flag():
    store = _tmp_store()
    m = RunGenMetrics(run_id="run-low")
    for _ in range(4):
        m.record_generation(all_gates_passed=False)
    store.save(m)

    rows = store.history()
    assert rows[0]["below_threshold"] == 1
    assert rows[0]["gate_pass_rate"] == pytest.approx(0.0)


def test_history_ordered_newest_first():
    store = _tmp_store()
    for i in range(3):
        m = RunGenMetrics(run_id=f"run-{i}")
        m.record_generation(all_gates_passed=True)
        store.save(m)

    rows = store.history()
    assert rows[0]["run_id"] == "run-2"
    assert rows[1]["run_id"] == "run-1"
    assert rows[2]["run_id"] == "run-0"


def test_history_respects_limit():
    store = _tmp_store()
    for i in range(5):
        m = RunGenMetrics(run_id=f"run-{i}")
        m.record_generation(all_gates_passed=True)
        store.save(m)

    rows = store.history(limit=2)
    assert len(rows) == 2


def test_trend_summary_no_data():
    store = _tmp_store()
    summary = store.trend_summary()
    assert "No generation metrics" in summary


def test_trend_summary_with_data():
    store = _tmp_store()
    m = RunGenMetrics(run_id="r1")
    m.record_generation(all_gates_passed=True)
    m.record_operation(covered=True)
    store.save(m)

    summary = store.trend_summary()
    assert "r1" in summary
    assert "pass=" in summary
    assert "cov=" in summary


def test_trend_summary_flags_below_threshold():
    store = _tmp_store()
    m = RunGenMetrics(run_id="low-run")
    for _ in range(4):
        m.record_generation(all_gates_passed=False)
    store.save(m)

    summary = store.trend_summary()
    assert "BELOW THRESHOLD" in summary


def test_gate_pass_threshold_constant():
    assert GATE_PASS_THRESHOLD == 0.75
