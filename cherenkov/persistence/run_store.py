"""Persistent run history for verify/validate/certify commands.

Each command invocation that completes writes a RunRecord here.
This is the foundation for `cherenkov report --diff` and trend analysis.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

_DEFAULT_DB = Path.home() / ".cherenkov" / "runs.db"
_BUSY_TIMEOUT_S = 10.0


RunStatus = Literal["running", "complete", "failed", "aborted"]


@dataclass
class RunRecord:
    """Placeholder docstring.

<description>"""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    command: str = ""                     # "verify" | "validate" | "certify" | "pipeline"
    target_url: str = ""
    spec_hash: str = ""                   # SHA-256 of spec bytes, "" if no spec
    verdict: Literal["PASS", "WARN", "FAIL", ""] = ""
    divergence_count: int = 0
    coverage_pct: float | None = None
    duration_ms: int = 0
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    meta_json: str = "{}"                 # arbitrary extra fields as JSON string
    # A run is written once at launch with status="running" and updated on
    # completion, so an in-flight run is addressable over HTTP rather than
    # existing only as a WebSocket broadcast a client may have missed.
    status: RunStatus = "complete"
    journey_id: str = ""                  # "" for runs not driven by a journey
    step_state_json: str = "{}"           # {step_id: {"status": ..., "duration_ms": ...}}
    failure_classification: Literal["product_bug", "test_fragility", "flake", ""] = ""


def _db_path() -> Path:
    env = os.getenv("CHERENKOV_RUNS_DB")
    return Path(env) if env else _DEFAULT_DB


class RunStore:
    """Placeholder docstring.

<description>"""
    def __init__(self, db_path: Path | None = None):
        self._path = db_path or _db_path()
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._path, timeout=_BUSY_TIMEOUT_S, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id          TEXT PRIMARY KEY,
                    command         TEXT NOT NULL,
                    target_url      TEXT NOT NULL DEFAULT '',
                    spec_hash       TEXT NOT NULL DEFAULT '',
                    verdict         TEXT NOT NULL DEFAULT '',
                    divergence_count INTEGER NOT NULL DEFAULT 0,
                    coverage_pct    REAL,
                    duration_ms     INTEGER NOT NULL DEFAULT 0,
                    timestamp       TEXT NOT NULL,
                    meta_json       TEXT NOT NULL DEFAULT '{}',
                    status          TEXT NOT NULL DEFAULT 'complete',
                    journey_id      TEXT NOT NULL DEFAULT '',
                    step_state_json TEXT NOT NULL DEFAULT '{}',
                    failure_classification TEXT NOT NULL DEFAULT ''
                )
            """)
            # Databases created before journey support predate the last four
            # columns. Adding them with a DEFAULT backfills existing rows.
            existing = {r["name"] for r in conn.execute("PRAGMA table_info(runs)")}
            for column, ddl in (
                ("status", "TEXT NOT NULL DEFAULT 'complete'"),
                ("journey_id", "TEXT NOT NULL DEFAULT ''"),
                ("step_state_json", "TEXT NOT NULL DEFAULT '{}'"),
                ("failure_classification", "TEXT NOT NULL DEFAULT ''"),
            ):
                if column not in existing:
                    conn.execute(f"ALTER TABLE runs ADD COLUMN {column} {ddl}")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON runs(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_target ON runs(target_url, timestamp)"
            )
            conn.commit()

    def save(self, record: RunRecord) -> RunRecord:
        """Placeholder docstring.

:param record: <description>
:return: <description>"""
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs
                  (run_id, command, target_url, spec_hash, verdict,
                   divergence_count, coverage_pct, duration_ms, timestamp, meta_json,
                   status, journey_id, step_state_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    record.run_id, record.command, record.target_url,
                    record.spec_hash, record.verdict, record.divergence_count,
                    record.coverage_pct, record.duration_ms, record.timestamp,
                    record.meta_json, record.status, record.journey_id,
                    record.step_state_json,
                ),
            )
            conn.commit()
        return record

    def update_status(
        self,
        run_id: str,
        status: RunStatus,
        step_state: dict[str, Any] | None = None,
    ) -> None:
        """Patch a live run's status without rewriting the whole record.

        Used while a pipeline is in flight, where the terminal fields
        (verdict, coverage, duration) are not yet known.
        """
        sets = ["status=?"]
        params: list[Any] = [status]
        if step_state is not None:
            sets.append("step_state_json=?")
            params.append(json.dumps(step_state))
        params.append(run_id)
        with self._lock, self._connect() as conn:
            conn.execute(f"UPDATE runs SET {', '.join(sets)} WHERE run_id=?", params)
            conn.commit()

    def get(self, run_id: str) -> RunRecord | None:
        """Placeholder docstring.

:param run_id: <description>
:return: <description>"""
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return _row_to_record(row) if row else None

    def list(
        """Placeholder docstring.

:param target_url: <description>
:param command: <description>
:param limit: <description>
:param status: <description>
:param journey_id: <description>
:return: <description>"""
        self,
        target_url: str | None = None,
        command: str | None = None,
        limit: int = 50,
        status: RunStatus | None = None,
        journey_id: str | None = None,
    ) -> list[RunRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if target_url:
            clauses.append("target_url=?")
            params.append(target_url)
        if command:
            clauses.append("command=?")
            params.append(command)
        if status:
            clauses.append("status=?")
            params.append(status)
        if journey_id:
            clauses.append("journey_id=?")
            params.append(journey_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM runs {where} ORDER BY timestamp DESC LIMIT ?", params
            ).fetchall()
        return [_row_to_record(r) for r in rows]

    def diff(self, run_id_a: str, run_id_b: str) -> dict:
        """Return a structured diff between two runs."""
        a = self.get(run_id_a)
        b = self.get(run_id_b)
        if not a or not b:
            missing = [r for r, rec in [(run_id_a, a), (run_id_b, b)] if rec is None]
            raise ValueError(f"Run(s) not found: {missing}")
        return {
            "run_a": run_id_a,
            "run_b": run_id_b,
            "divergence_delta": b.divergence_count - a.divergence_count,
            "verdict_changed": a.verdict != b.verdict,
            "verdict_a": a.verdict,
            "verdict_b": b.verdict,
            "coverage_delta": (
                round((b.coverage_pct or 0) - (a.coverage_pct or 0), 2)
                if a.coverage_pct is not None and b.coverage_pct is not None
                else None
            ),
            "timestamp_a": a.timestamp,
            "timestamp_b": b.timestamp,
        }

    def update_classification(self, run_id: str, classification: str) -> bool:
        """Update the failure classification for a run."""
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "UPDATE runs SET failure_classification=? WHERE run_id=?",
                (classification, run_id),
            )
            conn.commit()
            return cur.rowcount > 0


def _row_to_record(row: sqlite3.Row) -> RunRecord:
    return RunRecord(
        run_id=row["run_id"],
        command=row["command"],
        target_url=row["target_url"],
        spec_hash=row["spec_hash"],
        verdict=row["verdict"],
        divergence_count=row["divergence_count"],
        coverage_pct=row["coverage_pct"],
        duration_ms=row["duration_ms"],
        timestamp=row["timestamp"],
        meta_json=row["meta_json"],
        status=row["status"],
        journey_id=row["journey_id"],
        step_state_json=row["step_state_json"],
        failure_classification=row["failure_classification"]
    )
    """Placeholder docstring.

:param spec_bytes: <description>
:return: <description>"""


def spec_hash(spec_bytes: bytes) -> str:
    return hashlib.sha256(spec_bytes).hexdigest()


_store: RunStore | None = None
_store_lock = threading.Lock()
    """Placeholder docstring.

:return: <description>"""


def get_run_store() -> RunStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = RunStore()
    return _store
