#!/usr/bin/env python3
"""
smoke_test_reflector_cli.py — verifies the Reflector inspect surface renders
stats + idioms + self-audit against a seeded store.

Run:  PYTHONPATH=. python3 smoke_test_reflector_cli.py
"""

from __future__ import annotations

import sys
import tempfile
import time
import uuid
from pathlib import Path

from cherenkov.core.contracts import (
    DivergenceClass,
    Idiom,
    VerdictOutcome,
    VerdictRecord,
)
from cherenkov.reflector.store import VerdictStore
from cherenkov.reflector.cli import build_report


def main() -> int:
    db = str(Path(tempfile.mkdtemp()) / "verdicts.db")
    store = VerdictStore(db_path=db)

    # seed: a flip-flop signature (-> audit smell) + one idiom (-> idioms section)
    for outcome in (VerdictOutcome.ACCEPT, VerdictOutcome.REJECT):
        store.record_verdict(
            VerdictRecord(
                id=str(uuid.uuid4()),
                hypothesis_id=str(uuid.uuid4()),
                outcome=outcome,
                divergence_class=DivergenceClass.D1_SPEC_CODE,
                endpoint="GET /pet/{petId}",
                source="test",
                timestamp=int(time.time()),
            )
        )
    store.upsert_idiom(
        Idiom(
            id="i1",
            pattern="check unique(email) on create",
            divergence_class=DivergenceClass.D4_DB_CODE,
            endpoint="POST /user",
            confirm_count=3,
            last_confirmed=int(time.time()),
            decay_score=0.9,
        )
    )

    report = build_report(db)
    print(report)
    print()

    checks = {
        "stats section": "Reflector stats" in report,
        "verdict count = 2": "verdicts : 2" in report,
        "idioms section": "Top idioms" in report,
        "idiom listed": "unique(email)" in report,
        "audit ran": "self-audit" in report,
        "flip-flop caught": "flip_flop" in report,
    }
    for k, v in checks.items():
        print(f"  [{'ok' if v else 'XX'}] {k}")
    ok = all(checks.values())
    print(
        "\n[PASS] reflector CLI renders stats + idioms + self-audit"
        if ok
        else "\n[FAIL] see above"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
