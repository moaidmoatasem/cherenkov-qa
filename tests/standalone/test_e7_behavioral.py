"""
test_e7_behavioral.py — A6 #113 unit tests for E7 behavioral-exit criteria.

Verifies:
  1. fingerprint_of() is STABLE  — same hypothesis → same fingerprint.
  2. fingerprint_of() is DISTINCT — different hypotheses → different fingerprints.
  3. Rejected fingerprints are stored in the VerdictStore and retrieved correctly.
  4. SUPPRESSION: a hypothesis rejected once is filtered out by rerank() on the
     next call, regardless of whether the hypothesis carries a fresh UUID.

All tests use in-memory SQLite — no disk I/O, fully deterministic.
"""
from __future__ import annotations

import uuid

import pytest

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceHypothesis,
    ReproductionResult,
    Severity,
    VerdictOutcome,
)
from cherenkov.reflector.reflector import Reflector, fingerprint_of
from cherenkov.reflector.store import VerdictStore


# ── fixtures ──────────────────────────────────────────────────────────────────
import tempfile
import os

def _store() -> VerdictStore:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return VerdictStore(db_path=path)


def _reflector(store: VerdictStore | None = None) -> Reflector:
    return Reflector(store=store or _store())


def _make_hypothesis(
    *,
    divergence_class: DivergenceClass = DivergenceClass.D1_SPEC_CODE,
    endpoint: str = "GET /pet/findByStatus",
    claim_a: str = "spec: status enum only",
    claim_b: str = "impl accepts anything",
    severity: Severity = Severity.MEDIUM,
    fresh_id: bool = True,
) -> DivergenceHypothesis:
    return DivergenceHypothesis(
        id=str(uuid.uuid4()) if fresh_id else "fixed-id-0001",
        divergence_class=divergence_class,
        claim_a=claim_a,
        claim_b=claim_b,
        predicted_evidence="observable signal",
        severity=severity,
        endpoint=endpoint,
        repro_steps=["step 1"],
    )


def _rejected_result(hypothesis_id: str) -> ReproductionResult:
    return ReproductionResult(
        hypothesis_id=hypothesis_id,
        reproduced=False,
        rejection_reason="witness could not reproduce",
    )


# ── 1. fingerprint_of() stability ─────────────────────────────────────────────

class TestFingerprintStability:
    """Same hypothesis (content) must yield the same fingerprint, regardless of id."""

    def test_same_hypothesis_same_fingerprint(self):
        h1 = _make_hypothesis()
        h2 = _make_hypothesis()  # fresh UUID but identical content
        assert fingerprint_of(h1) == fingerprint_of(h2), (
            "Two hypotheses with identical class/endpoint/claims must share a fingerprint."
        )

    def test_fingerprint_is_deterministic_across_calls(self):
        h = _make_hypothesis()
        fp1 = fingerprint_of(h)
        fp2 = fingerprint_of(h)
        assert fp1 == fp2, "fingerprint_of() must be deterministic for the same object."

    def test_fingerprint_length(self):
        h = _make_hypothesis()
        fp = fingerprint_of(h)
        assert len(fp) == 16, f"Expected 16-hex fingerprint, got len={len(fp)}: {fp!r}"

    def test_fingerprint_is_string(self):
        h = _make_hypothesis()
        assert isinstance(fingerprint_of(h), str)


# ── 2. fingerprint_of() distinctness ─────────────────────────────────────────

class TestFingerprintDistinctness:
    """Different hypotheses must produce different fingerprints."""

    def test_different_claim_a(self):
        h1 = _make_hypothesis(claim_a="claim A version 1")
        h2 = _make_hypothesis(claim_a="claim A version 2")
        assert fingerprint_of(h1) != fingerprint_of(h2)

    def test_different_claim_b(self):
        h1 = _make_hypothesis(claim_b="impl does X")
        h2 = _make_hypothesis(claim_b="impl does Y")
        assert fingerprint_of(h1) != fingerprint_of(h2)

    def test_different_endpoint(self):
        h1 = _make_hypothesis(endpoint="GET /pet/findByStatus")
        h2 = _make_hypothesis(endpoint="POST /pet")
        assert fingerprint_of(h1) != fingerprint_of(h2)

    def test_different_divergence_class(self):
        h1 = _make_hypothesis(divergence_class=DivergenceClass.D1_SPEC_CODE)
        h2 = _make_hypothesis(divergence_class=DivergenceClass.D5_SPEC_PROD)
        assert fingerprint_of(h1) != fingerprint_of(h2)

    def test_whitespace_normalised(self):
        """Leading/trailing/double spaces are stripped in the fingerprint basis."""
        h1 = _make_hypothesis(claim_a="  spec: status enum  only  ")
        h2 = _make_hypothesis(claim_a="spec: status enum only")
        assert fingerprint_of(h1) == fingerprint_of(h2), (
            "Whitespace normalisation should make these fingerprints identical."
        )


# ── 3. Storage and retrieval of rejected fingerprints ─────────────────────────

class TestRejectedFingerprintStorage:
    """Rejected fingerprints must be persisted and retrievable from the store."""

    def test_fingerprint_stored_after_rejection(self):
        store = _store()
        reflector = _reflector(store)
        h = _make_hypothesis()

        reflector.ingest_from_reproduction(h, _rejected_result(h.id))

        stored = store.rejected_fingerprints()
        assert fingerprint_of(h) in stored, (
            f"Fingerprint {fingerprint_of(h)!r} should be in rejected_fingerprints "
            f"after rejection. Got: {stored}"
        )

    def test_accepted_hypothesis_not_in_rejected_fingerprints(self):
        store = _store()
        reflector = _reflector(store)
        h = _make_hypothesis()

        result = ReproductionResult(
            hypothesis_id=h.id,
            reproduced=True,
            evidence=DivergenceEvidence(
                request_summary="GET /pet/findByStatus → 200",
                response_actual={"pets": []},
                response_expected="400",
                diff="status 200 vs expected 400",
            ),
        )
        reflector.ingest_from_reproduction(h, result)

        stored = store.rejected_fingerprints()
        assert fingerprint_of(h) not in stored, (
            "Accepted hypothesis must NOT leave a rejected fingerprint."
        )

    def test_verdict_count_incremented(self):
        store = _store()
        reflector = _reflector(store)

        for i in range(3):
            h = _make_hypothesis(claim_a=f"claim A {i}", claim_b=f"claim B {i}")
            reflector.ingest_from_reproduction(h, _rejected_result(h.id))

        stats = reflector.get_stats()
        assert stats["verdict_count"] == 3, (
            f"Expected 3 verdicts stored, got {stats['verdict_count']}"
        )


# ── 4. Suppression: rejected → filtered by rerank() on next round ─────────────

class TestSuppressionViafFingerprint:
    """Core E7 behavioural-exit: rejected hypothesis must be suppressed on re-run."""

    def test_rejected_hypothesis_suppressed_on_rerank(self):
        """
        Scenario (mirrors the smoke test):
          1. Reject hypothesis h.
          2. Mint a FRESH hypothesis h2 with the SAME semantic content but new UUID.
          3. rerank([h2]) should return [].
        """
        store = _store()
        reflector = _reflector(store)

        # Step 1: generate and reject the original hypothesis
        h = _make_hypothesis()
        reflector.ingest_from_reproduction(h, _rejected_result(h.id))

        # Step 2: mint a fresh hypothesis with the same semantic content
        h2 = _make_hypothesis()  # fresh UUID, same class/endpoint/claims
        assert h.id != h2.id, "pre-condition: hypothesis IDs must differ"
        assert fingerprint_of(h) == fingerprint_of(h2), "pre-condition: fingerprints must match"

        # Step 3: rerank should suppress h2
        filtered = reflector.rerank([h2], endpoint=h2.endpoint)
        assert filtered == [], (
            f"Expected h2 to be suppressed (matching rejected fingerprint), "
            f"but rerank() returned: {filtered}"
        )

    def test_different_hypothesis_not_suppressed(self):
        """A hypothesis with DIFFERENT content must NOT be suppressed."""
        store = _store()
        reflector = _reflector(store)

        h = _make_hypothesis(claim_a="claim A version 1")
        reflector.ingest_from_reproduction(h, _rejected_result(h.id))

        h_different = _make_hypothesis(claim_a="claim A version 2")
        filtered = reflector.rerank([h_different], endpoint=h_different.endpoint)
        assert filtered == [h_different], (
            "A hypothesis with different content must NOT be suppressed."
        )

    def test_three_rejected_none_resurface(self):
        """
        Mirror of A6 smoke criteria: seed 3 rejections, confirm 0 resurface.
        """
        store = _store()
        reflector = _reflector(store)

        # Build 3 distinct hypotheses
        rejected_batch = [
            _make_hypothesis(
                claim_a=f"claim A variant {i}",
                claim_b=f"claim B variant {i}",
                endpoint=f"GET /endpoint/{i}",
            )
            for i in range(3)
        ]

        # Reject all 3
        for h in rejected_batch:
            reflector.ingest_from_reproduction(h, _rejected_result(h.id))

        # Build fresh hypotheses with same semantic content (new UUIDs)
        fresh_batch = [
            _make_hypothesis(
                claim_a=f"claim A variant {i}",
                claim_b=f"claim B variant {i}",
                endpoint=f"GET /endpoint/{i}",
            )
            for i in range(3)
        ]

        # Rerank each probe separately (as proof_run does)
        total_suppressed = 0
        for i, h_fresh in enumerate(fresh_batch):
            result = reflector.rerank([h_fresh], endpoint=h_fresh.endpoint)
            total_suppressed += len(fresh_batch) - len([result])
            assert result == [], (
                f"Fresh hypothesis #{i} should be suppressed (kill criterion 1 failed)."
            )

    def test_rerank_empty_list_returns_empty(self):
        """rerank([]) must return [] without error."""
        reflector = _reflector()
        assert reflector.rerank([]) == []

    def test_rerank_all_new_hypotheses_pass_through(self):
        """With no prior rejections, all hypotheses pass through rerank()."""
        reflector = _reflector()
        h1 = _make_hypothesis(claim_a="fresh claim 1")
        h2 = _make_hypothesis(claim_a="fresh claim 2")
        result = reflector.rerank([h1, h2])
        assert set(r.id for r in result) == {h1.id, h2.id}, (
            "All unseen hypotheses should pass through rerank()."
        )
