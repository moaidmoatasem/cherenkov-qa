"""Tests for cherenkov/verdict/mutation_oracle.py — MutationOracle."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from cherenkov.core.contracts import DivergenceClass, DivergenceHypothesis, Severity
from cherenkov.verdict.mutation_oracle import (
    Mutation,
    MutationOracle,
    MutationResult,
)


def _make_hypothesis(
    endpoint: str = "GET /test",
    divergence_class: DivergenceClass = DivergenceClass.D1_SPEC_CODE,
    repro_steps: list[str] | None = None,
) -> DivergenceHypothesis:
    return DivergenceHypothesis(
        id=str(uuid.uuid4()),
        divergence_class=divergence_class,
        claim_a="spec says X",
        claim_b="impl does Y",
        predicted_evidence="observable signal",
        severity=Severity.MEDIUM,
        endpoint=endpoint,
        repro_steps=repro_steps or ["Send GET /test", "Expect 400"],
    )


# ── Mutation dataclass ─────────────────────────────────────────────────────────

class TestMutation:
    def test_id_is_auto_generated(self):
        m = Mutation()
        assert m.id

    def test_defaults(self):
        m = Mutation()
        assert m.mutation_class == "STATUS_FLIP"
        assert m.expected_to_detect is True
        assert m.hypothesis is None

    def test_custom_fields(self):
        h = _make_hypothesis()
        m = Mutation(
            mutation_class="FIELD_DROP",
            description="drop photoUrls",
            hypothesis=h,
            expected_to_detect=True,
        )
        assert m.mutation_class == "FIELD_DROP"
        assert m.hypothesis == h


# ── MutationResult ─────────────────────────────────────────────────────────────

class TestMutationResult:
    def test_correct_when_detected_matches_expected(self):
        r = MutationResult(
            mutation_id="x",
            mutation_class="STATUS_FLIP",
            detected=True,
            expected_to_detect=True,
            correct=True,
        )
        assert r.correct is True

    def test_incorrect_when_missed_but_expected(self):
        r = MutationResult(
            mutation_id="x",
            mutation_class="STATUS_FLIP",
            detected=False,
            expected_to_detect=True,
            correct=False,
        )
        assert r.correct is False


# ── MutationOracle._build_mutations ───────────────────────────────────────────

class TestBuildMutations:
    def test_returns_at_least_three_mutations(self):
        oracle = MutationOracle.__new__(MutationOracle)
        mutations = oracle._build_mutations()
        assert len(mutations) >= 3

    def test_includes_negative_mutation(self):
        oracle = MutationOracle.__new__(MutationOracle)
        mutations = oracle._build_mutations()
        negative = [m for m in mutations if not m.expected_to_detect]
        assert len(negative) >= 1

    def test_includes_status_flip_class(self):
        oracle = MutationOracle.__new__(MutationOracle)
        mutations = oracle._build_mutations()
        classes = {m.mutation_class for m in mutations}
        assert "STATUS_FLIP" in classes

    def test_all_mutations_have_descriptions(self):
        oracle = MutationOracle.__new__(MutationOracle)
        mutations = oracle._build_mutations()
        assert all(m.description for m in mutations)


# ── MutationOracle._evaluate ───────────────────────────────────────────────────

class TestEvaluate:
    def test_mutation_without_hypothesis_returns_not_detected(self):
        oracle = MutationOracle.__new__(MutationOracle)
        oracle.witness = MagicMock()
        m = Mutation(hypothesis=None, expected_to_detect=True)
        result = oracle._evaluate(m)
        assert result.detected is False
        assert result.correct is False  # expected to detect, but no hypothesis to run

    def test_correctly_detected_mutation(self):
        from cherenkov.core.contracts import DivergenceEvidence, ReproductionResult

        evidence = DivergenceEvidence(
            request_summary="GET /test → 200 (10ms)",
            response_actual="{}",
            response_expected="400",
            diff="status mismatch: expected=400, actual=200",
        )
        mock_result = ReproductionResult(
            hypothesis_id="abc",
            reproduced=True,
            evidence=evidence,
        )
        oracle = MutationOracle.__new__(MutationOracle)
        oracle.witness = MagicMock()
        oracle.witness.reproduce.return_value = mock_result

        m = Mutation(hypothesis=_make_hypothesis(), expected_to_detect=True)
        result = oracle._evaluate(m)
        assert result.detected is True
        assert result.correct is True

    def test_witness_exception_returns_not_detected(self):
        oracle = MutationOracle.__new__(MutationOracle)
        oracle.witness = MagicMock()
        oracle.witness.reproduce.side_effect = RuntimeError("network error")
        m = Mutation(hypothesis=_make_hypothesis(), expected_to_detect=True)
        result = oracle._evaluate(m)
        assert result.detected is False
        assert "network error" in result.detail


# ── MutationOracle.run ─────────────────────────────────────────────────────────

class TestOracleRun:
    def test_score_between_0_and_1(self):
        from cherenkov.core.contracts import ReproductionResult

        oracle = MutationOracle.__new__(MutationOracle)
        oracle.base_url = "http://mock"
        oracle.witness = MagicMock()
        oracle.witness.reproduce.return_value = ReproductionResult(
            hypothesis_id="x", reproduced=False
        )
        report = oracle.run()
        assert 0.0 <= report.score <= 1.0

    def test_report_has_results_matching_mutation_count(self):
        from cherenkov.core.contracts import ReproductionResult

        oracle = MutationOracle.__new__(MutationOracle)
        oracle.base_url = "http://mock"
        oracle.witness = MagicMock()
        oracle.witness.reproduce.return_value = ReproductionResult(
            hypothesis_id="x", reproduced=False
        )
        mutations = oracle._build_mutations()
        report = oracle.run()
        assert report.mutations_run == len(mutations)

    def test_detected_plus_missed_equals_total(self):
        from cherenkov.core.contracts import ReproductionResult

        oracle = MutationOracle.__new__(MutationOracle)
        oracle.base_url = "http://mock"
        oracle.witness = MagicMock()
        oracle.witness.reproduce.return_value = ReproductionResult(
            hypothesis_id="x", reproduced=False
        )
        report = oracle.run()
        assert report.detected + report.missed == report.mutations_run
