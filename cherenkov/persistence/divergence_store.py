"""Persistent divergence findings for verify/certify runs.

`RunStore` records only the scalar `divergence_count` — the findings themselves
(endpoint, severity, claims, evidence, repro steps) were computed, printed to
the terminal, and then dropped. With nothing to read back, the dashboard's
`/api/v1/divergences` had no choice but to serve a hardcoded fixture. See #903.

This stores the sealed `DivergenceReport` artifacts produced by `run_proof`,
keyed to the `RunRecord` they belong to, so the API can serve real findings.

Deliberately mirrors `run_store.py`: same SQLite file, same WAL/busy-timeout
handling, same lazy module-level singleton. It is a sibling table, not a new
subsystem.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cherenkov.persistence.run_store import _db_path

_log = logging.getLogger(__name__)

_BUSY_TIMEOUT_S = 10.0

# Triage states a finding may be moved into. Mirrors the StatusType union in
# cherenkov/web/ui/src/types.ts — keep the two in step.
VALID_STATUSES = ("reproduced", "pending", "rejected", "live")


@dataclass
class FindingRecord:
    """One persisted divergence finding, flattened for storage.

    Field names track `DivergenceReport` (cherenkov/core/contracts.py) rather
    than the camelCase the web API emits; mapping to the wire shape is the web
    layer's job, not the store's.
    """

    finding_key: str = ""           # "{run_id}:{report.id}" — unique across runs
    run_id: str = ""
    report_id: str = ""
    divergence_class: str = ""      # e.g. "D1_spec_code"
    endpoint: str = ""
    severity: str = ""
    claim_a: str = ""
    claim_b: str = ""
    evidence_json: str = "{}"       # serialized DivergenceEvidence
    repro_steps_json: str = "[]"    # serialized list[str]
    status: str = "reproduced"
    timestamp: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )


class DivergenceStore:
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
                CREATE TABLE IF NOT EXISTS divergence_findings (
                    finding_key      TEXT PRIMARY KEY,
                    run_id           TEXT NOT NULL,
                    report_id        TEXT NOT NULL DEFAULT '',
                    divergence_class TEXT NOT NULL DEFAULT '',
                    endpoint         TEXT NOT NULL DEFAULT '',
                    severity         TEXT NOT NULL DEFAULT '',
                    claim_a          TEXT NOT NULL DEFAULT '',
                    claim_b          TEXT NOT NULL DEFAULT '',
                    evidence_json    TEXT NOT NULL DEFAULT '{}',
                    repro_steps_json TEXT NOT NULL DEFAULT '[]',
                    status           TEXT NOT NULL DEFAULT 'reproduced',
                    timestamp        TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_findings_run ON divergence_findings(run_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_findings_ts ON divergence_findings(timestamp)"
            )
            conn.commit()

    def save_reports(self, run_id: str, reports: list[Any]) -> int:
        """Persist the DivergenceReport objects belonging to one run.

        Accepts the pydantic models directly rather than importing the contract,
        so the persistence layer stays decoupled from core. Returns the number
        of findings written.
        """
        records = [_report_to_record(run_id, r) for r in reports]
        return self.save_many(records)

    def save_many(self, records: list[FindingRecord]) -> int:
        """Placeholder docstring.

:param records: <description>
:return: <description>"""
        if not records:
            return 0
        with self._lock, self._connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO divergence_findings
                  (finding_key, run_id, report_id, divergence_class, endpoint,
                   severity, claim_a, claim_b, evidence_json, repro_steps_json,
                   status, timestamp)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        r.finding_key, r.run_id, r.report_id, r.divergence_class,
                        r.endpoint, r.severity, r.claim_a, r.claim_b,
                        r.evidence_json, r.repro_steps_json, r.status, r.timestamp,
                    )
                    for r in records
                ],
            )
            conn.commit()
        return len(records)

    def list_for_run(self, run_id: str) -> list[FindingRecord]:
        """Placeholder docstring.

:param run_id: <description>
:return: <description>"""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM divergence_findings WHERE run_id=? ORDER BY timestamp DESC",
                (run_id,),
            ).fetchall()
        return [_row_to_record(r) for r in rows]

    def latest_run_id(self) -> str | None:
        """Run id of the most recent run that actually produced findings."""
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT run_id FROM divergence_findings ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
        return row["run_id"] if row else None

    def list_latest(self, limit: int = 200) -> list[FindingRecord]:
        """Findings from the most recent run that produced any.

        Scoped to a single run on purpose: mixing findings across runs would
        show the same endpoint repeatedly with stale verdicts.
        """
        run_id = self.latest_run_id()
        if run_id is None:
            return []
        return self.list_for_run(run_id)[:limit]

    def set_status(self, finding_key: str, status: str) -> bool:
        """Update triage status. Returns False if the finding is unknown."""
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {status}")
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "UPDATE divergence_findings SET status=? WHERE finding_key=?",
                (status, finding_key),
            )
            conn.commit()
            return cur.rowcount > 0

    def count(self) -> int:
        """Placeholder docstring.

:return: <description>"""
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM divergence_findings").fetchone()
        return int(row["n"])


def _report_to_record(run_id: str, report: Any) -> FindingRecord:
    """Flatten a DivergenceReport into a storable row.

    Uses getattr throughout so a plain object or namespace works as well as the
    pydantic model — the store should not care which produced it.
    """
    report_id = str(getattr(report, "id", "") or "")

    divergence_class = getattr(report, "divergence_class", "")
    divergence_class = getattr(divergence_class, "value", divergence_class) or ""

    severity = getattr(report, "severity", "")
    severity = getattr(severity, "value", severity) or ""

    evidence = getattr(report, "evidence", None)
    if evidence is not None and hasattr(evidence, "model_dump"):
        try:
            evidence_json = json.dumps(evidence.model_dump(), default=str)
        except (TypeError, ValueError):
            _log.debug("evidence serialization failed for %s", report_id, exc_info=True)
            evidence_json = "{}"
    else:
        evidence_json = json.dumps(evidence, default=str) if evidence else "{}"

    try:
        repro_steps_json = json.dumps(list(getattr(report, "repro_steps", []) or []), default=str)
    except (TypeError, ValueError):
        _log.debug("repro_steps serialization failed for %s", report_id, exc_info=True)
        repro_steps_json = "[]"

    return FindingRecord(
        finding_key=f"{run_id}:{report_id}",
        run_id=run_id,
        report_id=report_id,
        divergence_class=str(divergence_class),
        endpoint=str(getattr(report, "endpoint", "") or ""),
        severity=str(severity),
        claim_a=str(getattr(report, "claim_a", "") or ""),
        claim_b=str(getattr(report, "claim_b", "") or ""),
        evidence_json=evidence_json,
        repro_steps_json=repro_steps_json,
    )


def _row_to_record(row: sqlite3.Row) -> FindingRecord:
    return FindingRecord(
        finding_key=row["finding_key"],
        run_id=row["run_id"],
        report_id=row["report_id"],
        divergence_class=row["divergence_class"],
        endpoint=row["endpoint"],
        severity=row["severity"],
        claim_a=row["claim_a"],
        claim_b=row["claim_b"],
        evidence_json=row["evidence_json"],
        repro_steps_json=row["repro_steps_json"],
        status=row["status"],
        timestamp=row["timestamp"],
    )


_store: DivergenceStore | None = None
_store_lock = threading.Lock()
    """Placeholder docstring.

:return: <description>"""


def get_divergence_store() -> DivergenceStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = DivergenceStore()
    return _store


def reset_divergence_store() -> None:
    """Drop the cached singleton so a new CHERENKOV_RUNS_DB takes effect.

    Needed by tests, which point the env var at a tmp_path per case.
    """
    global _store
    with _store_lock:
        _store = None
