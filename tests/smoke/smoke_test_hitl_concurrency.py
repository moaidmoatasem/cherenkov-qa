#!/usr/bin/env python3
"""
smoke_test_hitl_concurrency.py — TRUE two-process race on one pending HITL item.
Stronger than the sequential IT1: two separate OS processes both fire approve;
SQLite serialization must yield exactly one winner + one conflict, regardless of
interleaving. Also proves enqueue does not resurrect a resolved item.

Run:  PYTHONPATH=. python3 smoke_test_hitl_concurrency.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from cherenkov.hitl import HitlItem, HitlQueue

WORKER = (
    "import json,os,sys,time\n"
    "from cherenkov.hitl import HitlQueue\n"
    "db,actor,go=sys.argv[1],sys.argv[2],sys.argv[3]\n"
    "q=HitlQueue(db_path=db)\n"
    "while not os.path.exists(go): time.sleep(0.005)\n"   # barrier: maximise contention
    "e=q.approve('ck_race',actor)\n"
    "print(json.dumps({'ok':e.ok,'code':(e.error.code if e.error else None),"
    "'actor':actor}))\n"
)


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    db = str(tmp / "hitl.db")
    go = str(tmp / "go.flag")
    q = HitlQueue(db_path=db)
    q.enqueue(HitlItem(id="ck_race", endpoint="/users/{id}", method="GET"))

    env = {**os.environ, "PYTHONPATH": os.getcwd()}
    procs = [subprocess.Popen([sys.executable, "-c", WORKER, db, who, go],
                              stdout=subprocess.PIPE, env=env)
             for who in ("@alice", "@bob")]
    time.sleep(0.2)                 # let both reach the barrier
    open(go, "w").close()           # fire
    outs = [json.loads(p.communicate()[0].decode().strip()) for p in procs]

    wins = [o for o in outs if o["ok"]]
    conflicts = [o for o in outs if not o["ok"] and o["code"] == "conflict"]
    item = q.get("ck_race")
    audit = [r["outcome"] for r in q.audit_rows()]

    # enqueue must NOT resurrect the now-resolved item
    q.enqueue(HitlItem(id="ck_race", endpoint="/users/{id}", method="GET"))
    not_resurrected = q.get("ck_race").status.value != "pending"

    checks = {
        "exactly one winner": len(wins) == 1,
        "exactly one conflict": len(conflicts) == 1,
        "winner owns the db row": item.approved_by == wins[0]["actor"] if wins else False,
        "audit has 1 success + 1 conflict": sorted(audit) == ["conflict", "success"],
        "enqueue does not resurrect resolved item": not_resurrected,
    }
    for k, ok in checks.items():
        print(f"  [{'ok' if ok else 'XX'}] {k}")
    print(f"\n  worker outputs: {outs}")

    passed = all(checks.values())
    print("\n[PASS] true 2-process race: SQLite serializes to one winner, audit intact"
          if passed else "\n[FAIL] see above")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
