#!/usr/bin/env python3
"""
smoke_test_hitl_race.py — proves the HITL queue the OpenClaw spec *claims* exists.
Implements the doc's IT1 (Alice/Bob race) plus not_found, reject, persistence, and
the frozen hitl/v1 envelope shape — the evidence the spec never produced.

Run:  PYTHONPATH=. python3 smoke_test_hitl_race.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from cherenkov.hitl import HitlItem, HitlQueue, SCHEMA_VERSION


def main() -> int:
    db = str(Path(tempfile.mkdtemp()) / "hitl.db")
    q = HitlQueue(db_path=db)
    q.enqueue(HitlItem(id="ck_1", endpoint="/users/{id}", method="GET",
                       mutation_label="Omit required field: email", confidence=0.78,
                       review_gate_failed="gate_3_ast", run_id="run_1"))

    checks = {}

    # IT1 — Alice wins the race, Bob gets a truthful conflict.
    a = q.approve("ck_1", "@alice")
    checks["alice success (rows_affected=1)"] = a.ok and a.payload["rows_affected"] == 1
    checks["alice envelope is hitl/v1"] = a.schema_version == SCHEMA_VERSION and a.command == "hitl.approve"

    b = q.approve("ck_1", "@bob")
    checks["bob conflict, not a lie"] = (not b.ok) and b.error.code == "conflict"
    checks["conflict names the winner"] = b.error.detail.get("current_actor") == "@alice" \
        and b.error.detail.get("current_status") == "approved"

    item = q.get("ck_1")
    checks["db SSOT correct"] = item.status.value == "approved" and item.approved_by == "@alice"

    audit = q.audit_rows()
    outcomes = [r["outcome"] for r in audit]
    checks["audit: exactly 1 success + 1 conflict"] = outcomes == ["success", "conflict"]

    # not_found
    nf = q.approve("ck_missing", "@x")
    checks["not_found code"] = (not nf.ok) and nf.error.code == "not_found"

    # reject path
    q.enqueue(HitlItem(id="ck_2", endpoint="/orders", method="POST"))
    r = q.reject("ck_2", "@bob", "incorrect_spec")
    checks["reject succeeds"] = r.ok and q.get("ck_2").status.value == "rejected" \
        and q.get("ck_2").reject_reason == "incorrect_spec"

    # persistence across a fresh queue handle
    checks["persists across instances"] = HitlQueue(db_path=db).get("ck_1").status.value == "approved"

    # frozen envelope shape (Appendix A)
    keys = set(a.model_dump().keys())
    checks["envelope shape exact"] = keys == {"schema_version", "ok", "command", "payload", "error"}

    for k, ok in checks.items():
        print(f"  [{'ok' if ok else 'XX'}] {k}")
    print(f"\n  alice envelope: {a.model_dump()}")
    print(f"  bob conflict:   {b.model_dump()}")

    passed = all(checks.values())
    print("\n[PASS] HITL queue: atomic race, truthful conflict, audit, persistence, hitl/v1 envelope"
          if passed else "\n[FAIL] see above")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
