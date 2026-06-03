"""
CHERENKOV reflector/store.py — SQLite persistence layer for E7 verdicts + idioms.

Pattern copied from stages/perf/perf_stage.py:_BaselineDB:
  - local SQLite in .cherenkov/
  - CREATE TABLE IF NOT EXISTS
  - simple insert / query
"""
from __future__ import annotations

import os
import sqlite3
import time
import uuid
from typing import Any

from cherenkov.core.contracts import (
    DivergenceClass,
    Idiom,
    ReflectorConfig,
    VerdictOutcome,
    VerdictRecord,
)
from cherenkov.core.errors import get_logger

# Local SQLite is shared across concurrent runs (daemon, proof_run, CLI inspect).
# Wait for a busy writer instead of failing fast with "database is locked".
_BUSY_TIMEOUT_S = 30.0


def _default_db_path() -> str:
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../..")
    )
    return os.path.join(repo_root, ".cherenkov", "verdicts.db")


class VerdictStore:
    """SQLite-backed persistence for VerdictRecord and Idiom storage.

    Tables:
      verdicts — one row per accept/reject/escaped-defect decision
      idioms   — per-system patterns with decay-score ranking
    """

    def __init__(self, db_path: str | None = None, run_id: str | None = None):
        self.db_path = db_path or _default_db_path()
        self.log = get_logger("REFLECTOR", run_id)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_tables()

    # ── schema ────────────────────────────────────────────────────────────

    def _init_tables(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS verdicts ("
            "id TEXT PRIMARY KEY,"
            "hypothesis_id TEXT NOT NULL,"
            "outcome TEXT NOT NULL,"
            "divergence_class TEXT,"
            "endpoint TEXT,"
            "failure_class TEXT,"
            "source TEXT NOT NULL DEFAULT 'skeptic',"
            "detail TEXT DEFAULT '',"
            "timestamp INTEGER NOT NULL,"
            "schema_version INTEGER NOT NULL DEFAULT 1)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS idioms ("
            "id TEXT PRIMARY KEY,"
            "pattern TEXT NOT NULL,"
            "divergence_class TEXT NOT NULL,"
            "endpoint TEXT,"
            "confirm_count INTEGER NOT NULL DEFAULT 1,"
            "last_confirmed INTEGER NOT NULL,"
            "decay_score REAL NOT NULL DEFAULT 1.0,"
            "schema_version INTEGER NOT NULL DEFAULT 1)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_verdicts_hypothesis "
            "ON verdicts(hypothesis_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_verdicts_outcome "
            "ON verdicts(outcome)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_verdicts_endpoint "
            "ON verdicts(endpoint)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_idioms_decay "
            "ON idioms(decay_score DESC)"
        )
        # E7 fix: suppress by SEMANTIC fingerprint, not ephemeral hypothesis_id.
        conn.execute(
            "CREATE TABLE IF NOT EXISTS rejected_fingerprints ("
            "fingerprint TEXT PRIMARY KEY,"
            "endpoint TEXT,"
            "divergence_class TEXT,"
            "timestamp INTEGER NOT NULL)"
        )
        conn.commit()
        conn.close()

    # ── verdict CRUD ──────────────────────────────────────────────────────

    def record_verdict(self, record: VerdictRecord) -> None:
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        conn.execute(
            "INSERT OR REPLACE INTO verdicts "
            "(id, hypothesis_id, outcome, divergence_class, endpoint, "
            " failure_class, source, detail, timestamp, schema_version) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                record.id,
                record.hypothesis_id,
                record.outcome.value,
                record.divergence_class.value if record.divergence_class else None,
                record.endpoint,
                record.failure_class,
                record.source,
                record.detail,
                record.timestamp or int(time.time()),
                record.schema_version,
            ),
        )
        conn.commit()
        conn.close()

    def get_verdict(self, verdict_id: str) -> VerdictRecord | None:
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        row = conn.execute(
            "SELECT * FROM verdicts WHERE id=?", (verdict_id,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return self._row_to_verdict(row)

    def get_verdicts_for_hypothesis(
        self, hypothesis_id: str
    ) -> list[VerdictRecord]:
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        rows = conn.execute(
            "SELECT * FROM verdicts WHERE hypothesis_id=? ORDER BY timestamp DESC",
            (hypothesis_id,),
        ).fetchall()
        conn.close()
        return [self._row_to_verdict(r) for r in rows]

    def get_rejected_hypothesis_ids(
        self, endpoint: str | None = None
    ) -> set[str]:
        """Return hypothesis IDs that were rejected (so they can be suppressed)."""
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        if endpoint:
            rows = conn.execute(
                "SELECT hypothesis_id FROM verdicts "
                "WHERE outcome=? AND endpoint=?",
                (VerdictOutcome.REJECT.value, endpoint),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT hypothesis_id FROM verdicts WHERE outcome=?",
                (VerdictOutcome.REJECT.value,),
            ).fetchall()
        conn.close()
        return {r[0] for r in rows}

    # ── fingerprint-based suppression (E7 fix) ───────────────────────────────

    def record_rejected_fingerprint(
        self, fingerprint: str, endpoint: str | None, divergence_class: str | None
    ) -> None:
        """Persist a semantic fingerprint so the SAME finding stays suppressed
        across runs even though the Skeptic re-mints a fresh hypothesis_id."""
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        conn.execute(
            "INSERT OR REPLACE INTO rejected_fingerprints "
            "(fingerprint, endpoint, divergence_class, timestamp) VALUES (?,?,?,?)",
            (fingerprint, endpoint, divergence_class, int(time.time())),
        )
        conn.commit()
        conn.close()

    def rejected_fingerprints(self, endpoint: str | None = None) -> set[str]:
        """Fingerprints to suppress. Scoped to an endpoint when given
        (NULL-endpoint rejections always apply)."""
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        if endpoint:
            rows = conn.execute(
                "SELECT fingerprint FROM rejected_fingerprints "
                "WHERE endpoint=? OR endpoint IS NULL",
                (endpoint,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT fingerprint FROM rejected_fingerprints"
            ).fetchall()
        conn.close()
        return {r[0] for r in rows}

    def get_recent_verdicts(
        self, limit: int = 50
    ) -> list[VerdictRecord]:
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        rows = conn.execute(
            "SELECT * FROM verdicts ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [self._row_to_verdict(r) for r in rows]

    # ── idiom CRUD ────────────────────────────────────────────────────────

    def upsert_idiom(self, idiom: Idiom) -> None:
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        conn.execute(
            "INSERT OR REPLACE INTO idioms "
            "(id, pattern, divergence_class, endpoint, confirm_count, "
            " last_confirmed, decay_score, schema_version) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                idiom.id,
                idiom.pattern,
                idiom.divergence_class.value,
                idiom.endpoint,
                idiom.confirm_count,
                idiom.last_confirmed or int(time.time()),
                idiom.decay_score,
                idiom.schema_version,
            ),
        )
        conn.commit()
        conn.close()

    def get_idioms(
        self, min_decay: float = 0.3, limit: int = 20
    ) -> list[Idiom]:
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        rows = conn.execute(
            "SELECT * FROM idioms WHERE decay_score >= ? "
            "ORDER BY decay_score DESC, confirm_count DESC LIMIT ?",
            (min_decay, limit),
        ).fetchall()
        conn.close()
        return [self._row_to_idiom(r) for r in rows]

    def get_idiom_by_pattern(self, pattern: str) -> Idiom | None:
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        row = conn.execute(
            "SELECT * FROM idioms WHERE pattern=?", (pattern,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return self._row_to_idiom(row)

    def decay_all_idioms(self, half_life_hours: float = 168.0) -> None:
        """Apply exponential time decay to all idiom decay_score values.

        decay_score *= 0.5 ^ (hours_elapsed / half_life_hours)
        """
        now = int(time.time())
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        rows = conn.execute(
            "SELECT id, last_confirmed, decay_score FROM idioms"
        ).fetchall()
        for row in rows:
            idiom_id, last_confirmed, decay_score = row
            hours_elapsed = (now - last_confirmed) / 3600.0
            if hours_elapsed > 0:
                factor = 0.5 ** (hours_elapsed / half_life_hours)
                decay_score = decay_score * factor
                conn.execute(
                    "UPDATE idioms SET decay_score=? WHERE id=?",
                    (round(decay_score, 4), idiom_id),
                )
        conn.commit()
        conn.close()

    def idiom_count(self) -> int:
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        count = conn.execute("SELECT COUNT(*) FROM idioms").fetchone()[0]
        conn.close()
        return count

    def verdict_count(self) -> int:
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        count = conn.execute("SELECT COUNT(*) FROM verdicts").fetchone()[0]
        conn.close()
        return count

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_verdict(row: sqlite3.Row | tuple) -> VerdictRecord:
        return VerdictRecord(
            id=row[0],
            hypothesis_id=row[1],
            outcome=VerdictOutcome(row[2]),
            divergence_class=DivergenceClass(row[3]) if row[3] else None,
            endpoint=row[4],
            failure_class=row[5],
            source=row[6],
            detail=row[7],
            timestamp=row[8],
            schema_version=row[9],
        )

    @staticmethod
    def _row_to_idiom(row: sqlite3.Row | tuple) -> Idiom:
        return Idiom(
            id=row[0],
            pattern=row[1],
            divergence_class=DivergenceClass(row[2]),
            endpoint=row[3],
            confirm_count=row[4],
            last_confirmed=row[5],
            decay_score=row[6],
            schema_version=row[7],
        )
