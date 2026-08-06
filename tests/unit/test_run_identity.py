"""Tests for durable run identity across the CLI/web boundary.

Before this, `POST /api/v1/run` returned a run_id that could never be looked
up: only the CLI verify/validate/certify paths called RunStore.save, so
GET /api/v1/runs and every /api/v1/coverage/* trend endpoint were structurally
blind to anything the dashboard triggered, and a client that missed the
/ws/live broadcast could not recover the outcome.
"""
from __future__ import annotations

import os
import sqlite3

os.environ.setdefault("CHERENKOV_ENV", "development")

import pytest

from cherenkov.persistence.run_store import RunRecord, RunStore


@pytest.fixture
def store(tmp_path) -> RunStore:
    return RunStore(db_path=tmp_path / "runs.db")


# ── Lifecycle ────────────────────────────────────────────────────────────

def test_run_defaults_to_complete_so_cli_callers_are_unchanged():
    """verify/validate/certify save once, at the end. They must stay correct
    without passing status explicitly."""
    assert RunRecord().status == "complete"
    assert RunRecord().journey_id == ""
    assert RunRecord().step_state_json == "{}"


def test_in_flight_run_is_addressable_before_it_finishes(store: RunStore):
    store.save(RunRecord(run_id="r1", command="pipeline", status="running"))

    record = store.get("r1")
    assert record is not None
    assert record.status == "running"
    assert record.verdict == ""  # not known yet


def test_update_status_patches_without_clobbering_terminal_fields(store: RunStore):
    store.save(RunRecord(
        run_id="r1", command="pipeline", target_url="http://api.test",
        spec_hash="abc123", status="running",
    ))

    store.update_status("r1", "running", {"ingest": {"status": "complete", "duration_ms": 12}})

    record = store.get("r1")
    assert record.target_url == "http://api.test"
    assert record.spec_hash == "abc123"
    assert record.step_state_json == '{"ingest": {"status": "complete", "duration_ms": 12}}'


def test_run_transitions_to_terminal_state(store: RunStore):
    store.save(RunRecord(run_id="r1", command="pipeline", status="running"))

    record = store.get("r1")
    record.status = "complete"
    record.verdict = "PASS"
    record.coverage_pct = 87.5
    record.duration_ms = 4200
    store.save(record)

    final = store.get("r1")
    assert (final.status, final.verdict, final.coverage_pct) == ("complete", "PASS", 87.5)


# ── Filtering ────────────────────────────────────────────────────────────

def test_list_filters_by_status_and_journey(store: RunStore):
    store.save(RunRecord(run_id="a", command="pipeline", status="running", journey_id="api-conformance"))
    store.save(RunRecord(run_id="b", command="pipeline", status="complete", journey_id="api-conformance"))
    store.save(RunRecord(run_id="c", command="verify", status="complete", journey_id=""))

    assert {r.run_id for r in store.list(status="running")} == {"a"}
    assert {r.run_id for r in store.list(journey_id="api-conformance")} == {"a", "b"}
    assert {r.run_id for r in store.list(status="complete", journey_id="api-conformance")} == {"b"}


# ── Migration ────────────────────────────────────────────────────────────

def _legacy_db(path) -> None:
    """Recreate the pre-journey schema, as shipped before this change."""
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY, command TEXT NOT NULL,
            target_url TEXT NOT NULL DEFAULT '', spec_hash TEXT NOT NULL DEFAULT '',
            verdict TEXT NOT NULL DEFAULT '', divergence_count INTEGER NOT NULL DEFAULT 0,
            coverage_pct REAL, duration_ms INTEGER NOT NULL DEFAULT 0,
            timestamp TEXT NOT NULL, meta_json TEXT NOT NULL DEFAULT '{}'
        )
    """)
    conn.execute(
        "INSERT INTO runs VALUES ('legacy','verify','http://old','','PASS',3,91.0,500,"
        "'2026-08-01T00:00:00Z','{}')"
    )
    conn.commit()
    conn.close()


def test_migration_preserves_existing_rows_and_backfills(tmp_path):
    db = tmp_path / "old.db"
    _legacy_db(db)

    record = RunStore(db_path=db).get("legacy")

    assert (record.verdict, record.divergence_count, record.coverage_pct) == ("PASS", 3, 91.0)
    # A pre-journey run is exactly what the backfill says it is: a finished,
    # non-journey run.
    assert record.status == "complete"
    assert record.journey_id == ""
    assert record.step_state_json == "{}"


def test_migration_is_idempotent(tmp_path):
    db = tmp_path / "old.db"
    _legacy_db(db)

    RunStore(db_path=db)
    RunStore(db_path=db)  # would raise "duplicate column name" if unguarded

    assert RunStore(db_path=db).get("legacy").status == "complete"


def test_migrated_db_accepts_new_writes(tmp_path):
    db = tmp_path / "old.db"
    _legacy_db(db)
    store = RunStore(db_path=db)

    store.save(RunRecord(run_id="new", command="pipeline", status="running", journey_id="j1"))

    assert store.get("new").journey_id == "j1"
    assert len(store.list()) == 2
