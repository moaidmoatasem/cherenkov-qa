#!/usr/bin/env python3
"""
smoke_test_reflector_suppression.py — proves E7's real behavioural exit:
a REJECTED finding stays suppressed across runs even though the Skeptic mints a
fresh hypothesis.id each run (fingerprint-based suppression).

Run:  PYTHONPATH=. python3 smoke_test_reflector_suppression.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceHypothesis,
    ReproductionResult,
    Severity,
)
from cherenkov.reflector.store import VerdictStore
from cherenkov.reflector.reflector import Reflector

EP = "GET /pet/{petId}"


def _hyp(hid: str, claim_a: str, claim_b: str) -> DivergenceHypothesis:
    return DivergenceHypothesis(
        id=hid,
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a=claim_a,
        claim_b=claim_b,
        predicted_evidence="HTTP 200 where spec promises 404",
        severity=Severity.MEDIUM,
        endpoint=EP,
        repro_steps=[],
    )


def main() -> int:
    db = str(Path(tempfile.mkdtemp()) / "verdicts.db")
    reflector = Reflector(VerdictStore(db_path=db))

    # Run 1: the Witness fails to reproduce → REJECT (records a fingerprint)
    h1 = _hyp("id-RUN1", "spec says 404 for missing pet", "code returns 200")
    reflector.ingest_from_reproduction(
        h1,
        ReproductionResult(
            hypothesis_id=h1.id,
            reproduced=False,
            rejection_reason="tautology / not reproduced",
        ),
    )

    # Run 2: Skeptic re-mints the SAME finding with a FRESH id, plus a genuinely
    # different finding that must survive.
    h_same = _hyp("id-RUN2-fresh", "spec says 404 for missing pet", "code returns 200")
    h_other = _hyp("id-RUN2-other", "spec says id is integer", "code accepts strings")
    reranked = reflector.rerank([h_same, h_other], endpoint=EP)
    ids = {h.id for h in reranked}

    suppressed_across_runs = "id-RUN2-fresh" not in ids  # THE behavioural exit
    other_survived = "id-RUN2-other" in ids  # no over-suppression

    # Persistence: a brand-new Reflector on the same store still suppresses it
    reflector2 = Reflector(VerdictStore(db_path=db))
    persisted = "id-RUN2-fresh" not in {
        h.id
        for h in reflector2.rerank(
            [_hyp("id-RUN3", "spec says 404 for missing pet", "code returns 200")],
            endpoint=EP,
        )
    }

    print(f"rerank(run2) kept ids = {sorted(ids)}")
    print(f"  suppressed re-minted rejection across runs : {suppressed_across_runs}")
    print(f"  genuinely-different finding survived        : {other_survived}")
    print(f"  suppression persists to a new Reflector     : {persisted}")

    ok = suppressed_across_runs and other_survived and persisted
    print(
        "\n[PASS] rejected findings stay suppressed across id re-minting (E7 exit met)"
        if ok
        else "\n[FAIL] see above"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
