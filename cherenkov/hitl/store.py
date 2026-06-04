"""
CHERENKOV hitl/store.py — the HITL queue (the prerequisite OpenClaw assumes).

SQLite is the concurrency gatekeeper: approve/reject are a single atomic
`UPDATE ... WHERE status='pending'`; `rows_affected` decides success vs conflict,
and the audit row is written in the SAME transaction. Correct even when every
voice layer is bypassed and a human uses the terminal.

Dedicated `.cherenkov/hitl.db` — follows the repo's one-DB-per-concern convention
(perf_metrics.db, verdicts.db), not a risky single-state.db big-bang. WAL +
busy-timeout so it survives concurrent runs (same hardening as reflector/store).
"""
from __future__ import annotations

import os
import sqlite3
import time

from cherenkov.hitl.contracts import (
    HitlEnvelope,
    HitlItem,
    HitlStatus,
    err_envelope,
    ok_envelope,
)

_BUSY_TIMEOUT_S = 30.0


def _default_db_path() -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    return os.path.join(root, ".cherenkov", "hitl.db")


class HitlQueue:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or _default_db_path()
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        return con

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
        # INSERT OR IGNORE — never resurrect/clobber an already-resolved item if
        # the same id is enqueued twice. Returns the stored item (existing wins).
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
        con.commit()
        con.close()
        return self.get(item.id) or item   # existing item wins on id collision

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
            cur = con.execute(
                f"UPDATE hitl_queue SET status=?, approved_by=?, approved_at=?{extra_sql} "
                "WHERE id=? AND status='pending'",
                (new_status.value, actor, _now(), *extra_vals, item_id),
            )
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

    def approve(self, item_id: str, actor: str, source: str = "cli") -> HitlEnvelope:
        return self._resolve("hitl.approve", item_id, actor, source,
                             HitlStatus.APPROVED, "", ())

    def reject(self, item_id: str, actor: str, reason: str, source: str = "cli") -> HitlEnvelope:
        return self._resolve("hitl.reject", item_id, actor, source,
                             HitlStatus.REJECTED, ", reject_reason=?", (reason,))


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
