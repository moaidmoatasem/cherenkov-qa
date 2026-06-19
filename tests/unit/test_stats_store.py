import os
import tempfile
import pytest
from cherenkov.core.stats_store import StatsStore


@pytest.fixture
def stats_store():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()
    store = StatsStore(db_path)
    yield store
    store.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_record_run(stats_store):
    stats_store.record_run(
        run_id="test-run",
        success=True,
        scenarios_passed=3,
        scenarios_total=3,
        total_duration_ms=45,
    )
    summary = stats_store.get_run_summary()
    assert summary["total_runs"] >= 1


def test_record_fail(stats_store):
    stats_store.record_run(
        run_id="fail-run", success=False, scenarios_passed=1, scenarios_total=3
    )
    summary = stats_store.get_run_summary()
    assert summary["total_runs"] == 1
    assert summary["successful_runs"] == 0


def test_get_run_summary_empty(stats_store):
    summary = stats_store.get_run_summary()
    assert summary["total_runs"] == 0
    assert summary["successful_runs"] == 0


def test_get_recent_runs(stats_store):
    stats_store.record_run(run_id="r1", success=True)
    stats_store.record_run(run_id="r2", success=True)
    runs = stats_store.get_recent_runs(limit=10)
    assert len(runs) == 2


def test_get_recent_runs_limit(stats_store):
    for i in range(5):
        stats_store.record_run(run_id=f"r{i}", success=True)
    runs = stats_store.get_recent_runs(limit=3)
    assert len(runs) == 3


def test_snapshot(stats_store):
    stats_store.snapshot(verdict_count=10, idiom_count=5, source="cli")
    # Read back via the underlying SQLite connection to assert the row was persisted.
    import sqlite3
    conn = sqlite3.connect(stats_store.db_path)
    rows = conn.execute(
        "SELECT verdict_count, idiom_count, source FROM snapshot_stats"
    ).fetchall()
    conn.close()
    assert len(rows) == 1, "snapshot() should have inserted exactly one row"
    assert rows[0][0] == 10, f"Expected verdict_count=10, got {rows[0][0]}"
    assert rows[0][1] == 5, f"Expected idiom_count=5, got {rows[0][1]}"
    assert rows[0][2] == "cli", f"Expected source='cli', got {rows[0][2]!r}"
