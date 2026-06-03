#!/usr/bin/env python3
"""
smoke_test_reflector_store_concurrency.py — proves the VerdictStore busy-timeout
lets concurrent runs serialize instead of crashing with "database is locked".

A separate PROCESS holds an exclusive write lock (mirrors concurrent agents).
  Control: a short-timeout connection RAISES 'database is locked'.
  Fix:     the hardened VerdictStore (timeout=30s) WAITS for the lock and succeeds.

Run:  PYTHONPATH=. python3 smoke_test_reflector_store_concurrency.py
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from cherenkov.core.contracts import DivergenceClass, VerdictOutcome, VerdictRecord
from cherenkov.reflector.store import VerdictStore


def _vr():
    return VerdictRecord(
        id=str(uuid.uuid4()), hypothesis_id=str(uuid.uuid4()),
        outcome=VerdictOutcome.REJECT, divergence_class=DivergenceClass.D1_SPEC_CODE,
        endpoint="GET /pet/{petId}", source="test", timestamp=int(time.time()),
    )


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    db = str(tmp / "verdicts.db")
    ready = str(tmp / "locked.flag")
    store = VerdictStore(db_path=db)  # create schema (hardened timeout)

    # Separate process grabs an exclusive write lock for ~1.2s.
    holder_src = (
        "import sqlite3, time\n"
        f"c = sqlite3.connect({db!r}); c.isolation_level = None\n"
        "c.execute('BEGIN EXCLUSIVE')\n"
        f"open({ready!r}, 'w').close()\n"
        "time.sleep(1.2)\n"
        "c.execute('COMMIT'); c.close()\n"
    )
    proc = subprocess.Popen([sys.executable, "-c", holder_src])
    while not os.path.exists(ready):       # wait until the lock is actually held
        time.sleep(0.02)

    # CONTROL — fail-fast writer cannot get in -> proves real contention.
    locked_fast = False
    ctrl = sqlite3.connect(db, timeout=0.1)
    try:
        ctrl.execute("INSERT INTO verdicts (id,hypothesis_id,outcome,timestamp) "
                     "VALUES (?,?,?,?)", ("ctrl", "h", "reject", 0))
        ctrl.commit()
    except sqlite3.OperationalError as e:
        locked_fast = "locked" in str(e).lower()
    finally:
        ctrl.close()

    # FIX — hardened store waits for the lock to clear, then writes.
    t0 = time.time()
    store.record_verdict(_vr())
    waited = time.time() - t0
    proc.wait(timeout=10)
    recorded = store.verdict_count() == 1

    print(f"control (timeout=0.1s) hit 'database is locked' : {locked_fast}")
    print(f"hardened store waited then succeeded            : {recorded} (waited {waited:.2f}s)")

    ok = locked_fast and recorded
    print("\n[PASS] busy-timeout serializes concurrent writers instead of crashing"
          if ok else "\n[FAIL] see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
