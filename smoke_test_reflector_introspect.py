#!/usr/bin/env python3
"""
smoke_test_reflector_introspect.py — proves the Reflector memory self-audit
catches each self-contradiction class. Raw-evidence style (no mocks of the store).

Run:  PYTHONPATH=. python3 smoke_test_reflector_introspect.py
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
from cherenkov.reflector.introspect import SmellType, audit_memory


def _vr(outcome, endpoint, cls, hid=None):
    return VerdictRecord(
        id=str(uuid.uuid4()),
        hypothesis_id=hid or str(uuid.uuid4()),
        outcome=outcome,
        divergence_class=cls,
        endpoint=endpoint,
        source="test",
        timestamp=int(time.time()),
    )


def main() -> int:
    tmp = Path(tempfile.mkdtemp()) / "verdicts.db"
    store = VerdictStore(db_path=str(tmp))

    # FLIP_FLOP: same endpoint+class accepted AND rejected (distinct ids)
    store.record_verdict(_vr(VerdictOutcome.ACCEPT, "GET /pet/{petId}", DivergenceClass.D1_SPEC_CODE))
    store.record_verdict(_vr(VerdictOutcome.REJECT, "GET /pet/{petId}", DivergenceClass.D1_SPEC_CODE))
    # clean signature (only accept) — must NOT flip-flop
    store.record_verdict(_vr(VerdictOutcome.ACCEPT, "POST /order", DivergenceClass.D4_DB_CODE))
    # EPHEMERAL_SUPPRESSION: a reject with a unique one-shot id
    store.record_verdict(_vr(VerdictOutcome.REJECT, "GET /store", DivergenceClass.D5_SPEC_PROD))

    # CONFLICTING_IDIOMS: two different patterns, same (endpoint, class)
    base = dict(divergence_class=DivergenceClass.D4_DB_CODE, endpoint="POST /user",
                confirm_count=2, last_confirmed=int(time.time()), decay_score=0.9)
    store.upsert_idiom(Idiom(id="i1", pattern="check unique(email) on create", **base))
    store.upsert_idiom(Idiom(id="i2", pattern="check tenant isolation on create", **base))
    # STALE_BELIEF: high confirm, decayed low
    store.upsert_idiom(Idiom(
        id="i3", pattern="validate phone is E.164", divergence_class=DivergenceClass.D3_UI_SPEC,
        endpoint="PUT /pet", confirm_count=7, last_confirmed=int(time.time()), decay_score=0.05,
    ))

    audit = audit_memory(store)
    print(audit.render())
    print()

    found = {s.type for s in audit.smells}
    expected = {
        SmellType.FLIP_FLOP,
        SmellType.CONFLICTING_IDIOMS,
        SmellType.STALE_BELIEF,
        SmellType.EPHEMERAL_SUPPRESSION,
    }
    missing = expected - found
    # negative check: the clean "POST /order" signature must not be a flip-flop
    flip_subjects = [s.subject for s in audit.smells if s.type == SmellType.FLIP_FLOP]
    false_positive = any("POST /order" in s for s in flip_subjects)

    ok = not missing and not false_positive
    print(f"verdicts={audit.verdicts_examined} idioms={audit.idioms_examined} "
          f"smells={len(audit.smells)} found={sorted(t.value for t in found)}")
    if missing:
        print(f"[FAIL] missing smell types: {sorted(t.value for t in missing)}")
    if false_positive:
        print("[FAIL] false-positive flip-flop on the clean signature")
    print("\n[PASS] memory self-audit catches all contradiction classes, no false positives"
          if ok else "\n[FAIL] see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
