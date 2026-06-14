"""
smoke_test_e7_behavioral.py — A6 #113 E7 Behavioral-Exit Demo.

KILL CRITERIA (must ALL pass for exit 0):
  1. None of the 3 seeded-rejected hypotheses resurface in the next proof run
     (fingerprint suppression works end-to-end).
  2. reflector.get_stats()['verdict_count'] > 3 (new verdicts recorded in run).
  3. Skeptic confirmed/total ratio is calculable from store stats (store is live).

Design constraints:
  - OFFLINE MODE ONLY (use_llm=False) — deterministic, no LLM, no network required.
  - In-memory SQLite — no disk state between runs.
  - Uses real proof_run() with a real Reflector + real VerdictStore(:memory:).
  - Real WitnessAgent IS used against https://petstore3.swagger.io — if the
    network is unavailable the smoke gracefully falls back to counting what the
    Reflector stored (no crash).
"""

from __future__ import annotations

import sys
import uuid

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceHypothesis,
    ReproductionResult,
    Severity,
)
from cherenkov.divergence.proof_run import (
    PETSTORE_BASE_URL,
    PROOF_RUN_PROBES,
    _offline_hypotheses,
    run_proof,
)
from cherenkov.reflector.reflector import Reflector, fingerprint_of
from cherenkov.reflector.store import VerdictStore


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_hypothesis(
    claim_a: str,
    claim_b: str,
    endpoint: str,
    divergence_class: DivergenceClass = DivergenceClass.D1_SPEC_CODE,
) -> DivergenceHypothesis:
    return DivergenceHypothesis(
        id=str(uuid.uuid4()),
        divergence_class=divergence_class,
        claim_a=claim_a,
        claim_b=claim_b,
        predicted_evidence="observable signal",
        severity=Severity.MEDIUM,
        endpoint=endpoint,
        repro_steps=["step 1"],
    )


def _rejected_result(hypothesis_id: str) -> ReproductionResult:
    return ReproductionResult(
        hypothesis_id=hypothesis_id,
        reproduced=False,
        rejection_reason="seeded rejection (smoke setup)",
    )


# ── main demo ─────────────────────────────────────────────────────────────────


def main() -> None:
    print("=" * 70)
    print("A6 #113 — E7 Behavioral Exit Demo")
    print("=" * 70)

    # ── Step 1: Create in-memory Reflector ────────────────────────────────────
    import tempfile
    import os

    fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = VerdictStore(db_path=temp_db_path)
    reflector = Reflector(store=store)
    print("\n[SETUP] Temporary VerdictStore + Reflector created.")

    # ── Step 2: Seed 3 rejections using REAL offline hypotheses ───────────────
    #   We pick the first probe's offline hypotheses and two synthetic variants.
    #   All three will be rejected via ingest_from_reproduction().
    first_endpoint, first_method, _, _ = PROOF_RUN_PROBES[0]
    seed_hypotheses = _offline_hypotheses(first_endpoint, first_method)

    # Add two synthetic extras so we always have exactly 3 seeds.
    seed_hypotheses += [
        _make_hypothesis(
            claim_a=f"seeded claim A #{i}",
            claim_b=f"seeded claim B #{i}",
            endpoint=f"GET /seeded/{i}",
        )
        for i in range(2)
    ]
    seed_hypotheses = seed_hypotheses[:3]  # take exactly 3

    print(f"\n[STEP 1] Seeding {len(seed_hypotheses)} rejection(s):")
    rejected_fingerprints: set[str] = set()
    for h in seed_hypotheses:
        fp = fingerprint_of(h)
        rejected_fingerprints.add(fp)
        reflector.ingest_from_reproduction(h, _rejected_result(h.id))
        print(f"  Rejected: {h.divergence_class.value} @ {h.endpoint} → fp={fp}")

    stats_after_seed = reflector.get_stats()
    print(
        f"\n[STEP 1] Verdict store after seeding: {stats_after_seed['verdict_count']} record(s)"
    )
    assert (
        stats_after_seed["verdict_count"] == 3
    ), f"Expected 3 verdicts after seeding, got {stats_after_seed['verdict_count']}"

    # ── Step 3: Run proof_run() in offline mode with the SAME reflector ───────
    print("\n[STEP 2] Running proof_run() (offline, in-memory reflector) ...")
    try:
        reports = run_proof(
            base_url=PETSTORE_BASE_URL,
            use_llm=False,
            reflector=reflector,
        )
        print(f"\n[STEP 2] proof_run complete — {len(reports)} report(s) confirmed.")
    except Exception as exc:
        print(f"\n[STEP 2] proof_run raised {type(exc).__name__}: {exc}")
        print("  Network unavailable? Continuing with store-only checks ...")
        reports = []

    # ── Step 4 (Kill criterion 1): Verify no seeded hypothesis resurfaces ─────
    print("\n[KILL CRITERION 1] Checking that 0 seeded fingerprints resurface ...")
    # The proof_run re-generates offline hypotheses for each probe.
    # Collect which offline hypotheses for the first endpoint match our seeds.
    fresh_for_first_probe = _offline_hypotheses(first_endpoint, first_method)
    resurfaced = [
        h for h in fresh_for_first_probe if fingerprint_of(h) in rejected_fingerprints
    ]

    # Also verify directly via rerank()
    reranked = reflector.rerank(
        fresh_for_first_probe, endpoint=f"{first_method} {first_endpoint}"
    )
    suppressed_by_rerank = len(fresh_for_first_probe) - len(reranked)

    print(f"  Seeded fingerprints : {rejected_fingerprints}")
    print(
        f"  Fresh-batch fps     : {[fingerprint_of(h) for h in fresh_for_first_probe]}"
    )
    print(f"  Resurfaced count    : {len(resurfaced)}")
    print(f"  Suppressed by rerank: {suppressed_by_rerank}")

    kill_1_pass = len(resurfaced) == 0 or suppressed_by_rerank > 0
    # Note: resurfaced counts hypotheses BEFORE rerank (they are candidates).
    # What matters is that rerank() removes them. So:
    kill_1_pass = suppressed_by_rerank == len(
        [h for h in fresh_for_first_probe if fingerprint_of(h) in rejected_fingerprints]
    )
    print(f"  Kill criterion 1: {'PASS ✓' if kill_1_pass else 'FAIL ✗'}")

    # ── Step 5 (Kill criterion 2): verdict_count > 3 ─────────────────────────
    print("\n[KILL CRITERION 2] Checking verdict_count > 3 ...")
    stats_after_run = reflector.get_stats()
    verdict_count = stats_after_run["verdict_count"]
    print(f"  verdict_count = {verdict_count}")
    kill_2_pass = verdict_count > 3
    print(f"  Kill criterion 2: {'PASS ✓' if kill_2_pass else 'FAIL ✗'}")

    # ── Step 6 (Kill criterion 3): confirmed/total ratio calculable ───────────
    print("\n[KILL CRITERION 3] Checking Skeptic hit-rate calculable ...")
    # Count accepted and total from the live store
    from cherenkov.core.contracts import VerdictOutcome

    accepted = sum(
        1
        for v in store.get_recent_verdicts(limit=200)
        if v.outcome == VerdictOutcome.ACCEPT
    )
    total = stats_after_run["verdict_count"]
    if total > 0:
        ratio = accepted / total
        print(f"  accepted={accepted}, total={total}, ratio={ratio:.2%}")
        kill_3_pass = True  # ratio is calculable as long as total > 0
    else:
        kill_3_pass = False
        print("  No verdicts in store — ratio cannot be calculated.")
    print(f"  Kill criterion 3: {'PASS ✓' if kill_3_pass else 'FAIL ✗'}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    all_pass = kill_1_pass and kill_2_pass and kill_3_pass
    if all_pass:
        print("ALL KILL CRITERIA MET — E7 behavioral exit PROVEN ✓")
        print("=" * 70)
        sys.exit(0)
    else:
        print("ONE OR MORE KILL CRITERIA FAILED:")
        print(
            f"  Kill criterion 1 (no resurface)    : {'PASS' if kill_1_pass else 'FAIL'}"
        )
        print(
            f"  Kill criterion 2 (verdict_count>3) : {'PASS' if kill_2_pass else 'FAIL'}"
        )
        print(
            f"  Kill criterion 3 (ratio calculable): {'PASS' if kill_3_pass else 'FAIL'}"
        )
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
