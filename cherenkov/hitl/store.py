"""
CHERENKOV hitl/store.py — the HITL queue (the prerequisite OpenClaw assumes).

SQLite is the concurrency gatekeeper: approve/reject are a single atomic
`UPDATE ... WHERE status='pending'`; `rows_affected` decides success vs conflict,
and the audit row is written in the SAME transaction. Correct even when every
voice layer is bypassed and a human uses the terminal.

Dedicated `.cherenkov/hitl.db` — follows the repo's one-DB-per-concern convention
(perf_metrics.db, verdicts.db), not a risky single-state.db big-bang. WAL +
busy-timeout so it survives concurrent runs (same hardening as reflector/store).

[Issue #196] At-rest encryption: set CHERENKOV_DB_KEY to enable SQLCipher-based
encryption. Falls back to plain SQLite if pysqlcipher3 is not available.
"""
from __future__ import annotations

import os as _os
import os
import sqlite3
import time
import logging

from cherenkov.hitl.contracts import (
    HitlEnvelope,
    HitlItem,
    HitlStatus,
    err_envelope,
    ok_envelope,
)

_BUSY_TIMEOUT_S = 30.0

# ── Issue #196: At-rest encryption ─────────────────────────────────────────
_DB_KEY = os.getenv("CHERENKOV_DB_KEY", "")

def _get_connection(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection, optionally with encryption if CHERENKOV_DB_KEY is set."""
    if _DB_KEY:
        try:
            import pysqlcipher3.dbapi2 as sqlcipher
            con = sqlcipher.connect(db_path, timeout=_BUSY_TIMEOUT_S)
            safe_key = _DB_KEY.replace("'", "''")
            con.execute(f"PRAGMA key='{safe_key}'")
            con.execute("PRAGMA cipher_page_size=4096")
            con.execute("PRAGMA kdf_iter=64000")
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA journal_mode=WAL")
            return con
        except ImportError:
            logging.getLogger("HITL").warning(
                "CHERENKOV_DB_KEY is set but pysqlcipher3 is not installed. "
                "Falling back to plain SQLite. Install with: pip install pysqlcipher3-binary"
            )
        except Exception as e:
            logging.getLogger("HITL").warning(
                "SQLCipher init failed, falling back to plain SQLite", exc_info=e
            )
    con = sqlite3.connect(db_path, timeout=_BUSY_TIMEOUT_S)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def _default_db_path() -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    return os.path.join(root, ".cherenkov", "hitl.db")


def _validate_db_path(path: str) -> str:
    if path == ":memory:":
        return path
    resolved = _os.path.realpath(_os.path.abspath(path))
    if not resolved.endswith(".db"):
        raise ValueError(f"db_path must end with .db, got: {path!r}")
    parent = _os.path.dirname(resolved)
    if not _os.path.exists(parent):
        _os.makedirs(parent, exist_ok=True)
    return resolved


class HitlQueue:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = _validate_db_path(db_path or _default_db_path())
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return _get_connection(self.db_path)

    def _init(self) -> None:
        con = self._connect()
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS hitl_queue (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                endpoint TEXT, method TEXT, mutation_id TEXT, mutation_label TEXT,
                confidence REAL, confidence_reason TEXT, review_gate_failed TEXT,
                approved_by TEXT, approved_at TEXT, reject_reason TEXT,
                run_id TEXT, spec_hash TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL, actor TEXT NOT NULL, source TEXT NOT NULL,
                item_id TEXT, outcome TEXT, rows_affected INTEGER, timestamp TEXT
            );
            """
        )
        con.commit()
        con.close()

    # ── reads ────────────────────────────────────────────────────────────
    def enqueue(self, item: HitlItem) -> HitlItem:
        # INSERT OR IGNORE — never resurrect/clobber an already-resolved item.
        # After insert, update endpoint/method on still-pending items so re-runs
        # back-fill metadata that was missing on first enqueue.
        con = self._connect()
        con.execute(
            "INSERT OR IGNORE INTO hitl_queue (id,status,endpoint,method,mutation_id,"
            "mutation_label,confidence,confidence_reason,review_gate_failed,approved_by,"
            "approved_at,reject_reason,run_id,spec_hash,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (item.id, item.status.value, item.endpoint, item.method, item.mutation_id,
             item.mutation_label, item.confidence, item.confidence_reason,
             item.review_gate_failed, item.approved_by, item.approved_at,
             item.reject_reason, item.run_id, item.spec_hash, item.created_at),
        )
        # Back-fill endpoint/method on pending items that were enqueued without them
        if item.endpoint or item.method:
            con.execute(
                "UPDATE hitl_queue SET endpoint=?, method=? "
                "WHERE id=? AND status='pending' AND (endpoint IS NULL OR method IS NULL)",
                (item.endpoint, item.method, item.id),
            )
        con.commit()
        con.close()
        return self.get(item.id) or item

    def get(self, item_id: str) -> HitlItem | None:
        con = self._connect()
        row = con.execute("SELECT * FROM hitl_queue WHERE id=?", (item_id,)).fetchone()
        con.close()
        return HitlItem(**{k: row[k] for k in row.keys()}) if row else None

    def list(self, status: str | None = "pending") -> list[HitlItem]:
        con = self._connect()
        if status:
            rows = con.execute("SELECT * FROM hitl_queue WHERE status=? ORDER BY created_at",
                               (status,)).fetchall()
        else:
            rows = con.execute("SELECT * FROM hitl_queue ORDER BY created_at").fetchall()
        con.close()
        return [HitlItem(**{k: r[k] for k in r.keys()}) for r in rows]

    def audit_rows(self) -> list[dict]:
        con = self._connect()
        rows = con.execute("SELECT * FROM audit_log ORDER BY id").fetchall()
        con.close()
        return [dict(r) for r in rows]

    # ── atomic mutations → frozen envelope ─────────────────────────────────
    def _resolve(self, command: str, item_id: str, actor: str, source: str,
                 new_status: HitlStatus, extra_sql: str, extra_vals: tuple) -> HitlEnvelope:
        con = self._connect()
        try:
            sql = "UPDATE hitl_queue SET status=?, approved_by=?, approved_at=? WHERE id=? AND status='pending'"
            vals = (new_status.value, actor, _now(), item_id)
            if extra_sql:
                sql = "UPDATE hitl_queue SET status=?, approved_by=?, approved_at=?, reject_reason=? WHERE id=? AND status='pending'"
                vals = (new_status.value, actor, _now(), extra_vals[0], item_id)
            
            cur = con.execute(sql, vals)
            rows = cur.rowcount
            if rows == 1:
                outcome = "success"
            else:
                exists = con.execute("SELECT status, approved_by, approved_at FROM hitl_queue "
                                     "WHERE id=?", (item_id,)).fetchone()
                outcome = "not_found" if exists is None else "conflict"
            # audit in the SAME transaction as the status change
            con.execute(
                "INSERT INTO audit_log (command,actor,source,item_id,outcome,rows_affected,timestamp) "
                "VALUES (?,?,?,?,?,?,?)",
                (command, actor, source, item_id, outcome, rows, _now()),
            )
            con.commit()
        finally:
            pass

        if outcome == "success":
            env = ok_envelope(command, {
                "id": item_id, "action": command.split(".")[-1],
                "previous_status": "pending", "current_status": new_status.value,
                "actor": actor, "actor_at": _now(), "rows_affected": 1,
            })
        elif outcome == "not_found":
            env = err_envelope(command, "not_found", f"{item_id} not found.", {"id": item_id})
        else:
            env = err_envelope(command, "conflict",
                               f"{item_id} no longer pending. Already {exists['status']} by "
                               f"{exists['approved_by']}.",
                               {"current_status": exists["status"],
                                "current_actor": exists["approved_by"],
                                "current_actor_at": exists["approved_at"]})
        con.close()
        return env

    def optimistic_lock(self, item_id: str, reviewer: str) -> bool:
        """Try to acquire an optimistic lock on a pending item.

        Sets the item's approved_by to the reviewer as a lock marker.
        Returns True if lock acquired, False if already locked/resolved.
        """
        con = self._connect()
        cur = con.execute(
            "UPDATE hitl_queue SET approved_by=?, approved_at=? "
            "WHERE id=? AND status='pending' AND approved_by IS NULL",
            (reviewer, _now(), item_id),
        )
        locked = cur.rowcount == 1
        con.commit()
        con.close()
        return locked

    def approve(self, item_id: str, actor: str, source: str = "cli") -> HitlEnvelope:
        return self._resolve("hitl.approve", item_id, actor, source,
                             HitlStatus.APPROVED, "", ())

    def reject(self, item_id: str, actor: str, reason: str, source: str = "cli") -> HitlEnvelope:
        return self._resolve("hitl.reject", item_id, actor, source,
                             HitlStatus.REJECTED, ", reject_reason=?", (reason,))


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# HitlStore is an alias for HitlQueue (enables external code / tests to use either name)
HitlStore = HitlQueue
