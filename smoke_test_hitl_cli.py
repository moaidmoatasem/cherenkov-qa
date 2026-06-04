#!/usr/bin/env python3
"""
smoke_test_hitl_cli.py — kill-criteria exit demo for HITL terminal CLI (A1 #109).

Proves the full enqueue → list → show → approve → reject → conflict cycle
using the cmd.py handlers against an in-memory DB. Emits a hitl/v1 JSON envelope
for each operation and verifies the schema_version and ok/error shape.

Run: PYTHONPATH=. python3 smoke_test_hitl_cli.py
Exit 0 = all checks pass (the kill criterion for A1).
"""
from __future__ import annotations

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import contextlib

from cherenkov.hitl import HitlItem, HitlQueue, SCHEMA_VERSION
from cherenkov.hitl.cmd import run_list, run_show, run_approve, run_reject


def capture_json(fn, *args, **kwargs) -> tuple[int, dict]:
    """Capture stdout from a --json call and parse it."""
    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*args, **kwargs)
    return rc, json.loads(buf.getvalue())


def main() -> int:
    db = str(Path(tempfile.mkdtemp()) / "smoke_hitl_cli.db")
    q = HitlQueue(db_path=db)

    checks: dict[str, bool] = {}

    # ── Seed: enqueue 2 items ─────────────────────────────────────────────
    q.enqueue(HitlItem(
        id="ck_smoke_1",
        endpoint="/users/{id}",
        method="GET",
        mutation_label="Omit required field: email",
        confidence=0.78,
        review_gate_failed="gate_ast",
        run_id="smoke_run_001",
    ))
    q.enqueue(HitlItem(
        id="ck_smoke_2",
        endpoint="/orders",
        method="POST",
        mutation_label="Status enum violation",
        confidence=0.73,
        review_gate_failed="gate_assertions",
        run_id="smoke_run_001",
    ))

    # ── list (JSON) — 2 pending ────────────────────────────────────────────
    rc, data = capture_json(run_list, status="pending", json_out=True, db_path=db)
    checks["list: rc=0"] = (rc == 0)
    checks["list: schema_version=hitl/v1"] = data.get("schema_version") == SCHEMA_VERSION
    checks["list: ok=True"] = data.get("ok") is True
    checks["list: command=hitl.list"] = data.get("command") == "hitl.list"
    checks["list: 2 items pending"] = data["payload"]["count"] == 2

    # ── show (JSON) — found ────────────────────────────────────────────────
    rc, data = capture_json(run_show, "ck_smoke_1", json_out=True, db_path=db)
    checks["show: rc=0"] = (rc == 0)
    checks["show: ok=True"] = data.get("ok") is True
    checks["show: command=hitl.show"] = data.get("command") == "hitl.show"
    checks["show: item.id matches"] = data["payload"]["item"]["id"] == "ck_smoke_1"
    checks["show: item.endpoint correct"] = data["payload"]["item"]["endpoint"] == "/users/{id}"

    # ── show (JSON) — not found ────────────────────────────────────────────
    stderr_buf = StringIO()
    with contextlib.redirect_stderr(stderr_buf):
        rc_nf, data_nf = capture_json(run_show, "ghost", json_out=True, db_path=db)
    checks["show not_found: rc=1"] = (rc_nf == 1)
    checks["show not_found: ok=False"] = data_nf.get("ok") is False
    checks["show not_found: error.code=not_found"] = data_nf.get("error", {}).get("code") == "not_found"

    # ── approve alice (JSON) ───────────────────────────────────────────────
    rc, data = capture_json(run_approve, "ck_smoke_1", actor="@alice",
                            json_out=True, db_path=db)
    checks["approve: rc=0"] = (rc == 0)
    checks["approve: ok=True"] = data.get("ok") is True
    checks["approve: command=hitl.approve"] = data.get("command") == "hitl.approve"
    checks["approve: rows_affected=1"] = data["payload"]["rows_affected"] == 1
    checks["approve: actor=@alice"] = data["payload"]["actor"] == "@alice"
    checks["approve: schema_version correct"] = data.get("schema_version") == SCHEMA_VERSION

    # DB state verification
    item = q.get("ck_smoke_1")
    checks["approve: DB status=approved"] = item.status.value == "approved"
    checks["approve: DB approved_by=@alice"] = item.approved_by == "@alice"

    # ── approve conflict (bob tries after alice) ───────────────────────────
    stderr_buf2 = StringIO()
    with contextlib.redirect_stderr(stderr_buf2):
        rc_c, data_c = capture_json(run_approve, "ck_smoke_1", actor="@bob",
                                    json_out=True, db_path=db)
    checks["conflict: rc=1"] = (rc_c == 1)
    checks["conflict: ok=False"] = data_c.get("ok") is False
    checks["conflict: error.code=conflict"] = data_c.get("error", {}).get("code") == "conflict"
    checks["conflict: names winner=@alice"] = (
        data_c.get("error", {}).get("detail", {}).get("current_actor") == "@alice"
    )
    checks["conflict: current_status=approved"] = (
        data_c.get("error", {}).get("detail", {}).get("current_status") == "approved"
    )

    # ── reject ck_smoke_2 ─────────────────────────────────────────────────
    rc, data = capture_json(run_reject, "ck_smoke_2",
                            reason="false_positive_spec_mismatch",
                            actor="@carol", json_out=True, db_path=db)
    checks["reject: rc=0"] = (rc == 0)
    checks["reject: ok=True"] = data.get("ok") is True
    checks["reject: command=hitl.reject"] = data.get("command") == "hitl.reject"

    item2 = q.get("ck_smoke_2")
    checks["reject: DB status=rejected"] = item2.status.value == "rejected"
    checks["reject: DB reject_reason correct"] = (
        item2.reject_reason == "false_positive_spec_mismatch"
    )

    # ── list --all shows 0 pending now ─────────────────────────────────────
    rc, data = capture_json(run_list, status="pending", json_out=True, db_path=db)
    checks["post-resolve list: 0 pending"] = (rc == 0 and data["payload"]["count"] == 0)

    rc_all, data_all = capture_json(run_list, status=None, json_out=True, db_path=db)
    checks["post-resolve list-all: 2 total"] = (rc_all == 0 and data_all["payload"]["count"] == 2)

    # ── actor defaulting via $USER ─────────────────────────────────────────
    q.enqueue(HitlItem(id="ck_env_actor", endpoint="/env", method="GET"))
    import os
    from unittest.mock import patch as mp
    with mp.dict(os.environ, {"USER": "env_tester"}):
        rc_env, data_env = capture_json(run_approve, "ck_env_actor", actor=None,
                                        json_out=True, db_path=db)
    checks["actor default: uses $USER"] = (
        rc_env == 0 and data_env["payload"]["actor"] == "env_tester"
    )

    # ── envelope shape invariant ───────────────────────────────────────────
    expected_keys = {"schema_version", "ok", "command", "payload", "error"}
    checks["envelope keys: exact match"] = set(data.keys()) == expected_keys

    # ── Print results ──────────────────────────────────────────────────────
    print("\nHITL CLI Smoke Test — A1 #109")
    print("=" * 60)
    for name, ok in checks.items():
        marker = "ok" if ok else "XX"
        print(f"  [{marker}] {name}")

    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\n[FAIL] {len(failed)} check(s) failed:")
        for f in failed:
            print(f"  - {f}")
        return 1

    print(f"\n[PASS] All {len(checks)} checks passed — HITL CLI kill criterion met.")
    print("       cherenkov hitl list|show|approve|reject --json ✓")
    print("       hitl/v1 envelope shape invariant ✓")
    print("       atomic conflict detection ✓")
    print("       actor defaulting via $USER ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
