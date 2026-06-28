"""Tests for cherenkov/verdict/semantic_judge.py — SemanticJudge."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceHypothesis,
    DivergenceReport,
    Severity,
    StageMeta,
    Status,
)
from cherenkov.verdict.semantic_judge import (
    EvidenceEvaluation,
    SemanticJudge,
    SemanticJudgeReport,
)


def _make_report(
    diff: str = "status mismatch: expected=400, actual=200",
    claim_a: str = "spec: status must be enum",
    claim_b: str = "impl accepts any value",
    repro_steps: int = 2,
) -> DivergenceReport:
    return DivergenceReport(
        id=str(uuid.uuid4()),
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a=claim_a,
        claim_b=claim_b,
        evidence=DivergenceEvidence(
            request_summary="GET /test → 200 (45ms)",
            response_actual={"status": "ok"},
            response_expected="400",
            diff=diff,
        ),
        repro_steps=[f"Step {i}" for i in range(repro_steps)],
        severity=Severity.MEDIUM,
        status=Status.OK,
        metadata=StageMeta(stage="test"),
    )


# ── EvidenceEvaluation ────────────────────────────────────────────────────────

class TestEvidenceEvaluation:
    def test_construction(self):
        e = EvidenceEvaluation(
            report_id="abc",
            quality_score=0.8,
            label="strong",
            rationale="clear diff",
        )
        assert e.quality_score == 0.8
        assert e.label == "strong"

    def test_default_fp_risk(self):
        e = EvidenceEvaluation(
            report_id="abc", quality_score=0.5, label="weak", rationale="x"
        )
        assert e.false_positive_risk == "low"


# ── SemanticJudgeReport ───────────────────────────────────────────────────────

class TestSemanticJudgeReport:
    def test_aggregate_score_range(self):
        r = SemanticJudgeReport(aggregate_score=0.75)
        assert 0.0 <= r.aggregate_score <= 1.0

    def test_fallback_flag(self):
        r = SemanticJudgeReport(aggregate_score=0.5, fallback=True)
        assert r.fallback is True


# ── SemanticJudge._score_heuristic ───────────────────────────────────────────

class TestScoreHeuristic:
    def test_strong_evidence_gets_high_score(self):
        report = _make_report(
            diff="status mismatch: expected=400, actual=200",
            claim_a="spec: 'status' enum must be 400",
        )
        score, label, rationale, fp_risk = SemanticJudge._score_heuristic(report)
        assert score >= 0.5
        assert label in ("strong", "weak")

    def test_empty_diff_gets_low_score(self):
        report = _make_report(diff="", claim_a="vague claim")
        score, label, rationale, fp_risk = SemanticJudge._score_heuristic(report)
        assert score < 0.5

    def test_no_repro_steps_reduces_score(self):
        report = _make_report(repro_steps=0)
        score_0, _, _, _ = SemanticJudge._score_heuristic(report)
        report2 = _make_report(repro_steps=2)
        score_2, _, _, _ = SemanticJudge._score_heuristic(report2)
        assert score_2 >= score_0

    def test_returns_four_values(self):
        report = _make_report()
        result = SemanticJudge._score_heuristic(report)
        assert len(result) == 4
        score, label, rationale, fp_risk = result
        assert isinstance(score, float)
        assert label in ("strong", "weak", "false_positive", "inconclusive")
        assert fp_risk in ("low", "medium", "high")


# ── SemanticJudge.evaluate ────────────────────────────────────────────────────

class TestEvaluate:
    def test_empty_reports_returns_perfect_score(self):
        judge = SemanticJudge()
        result = judge.evaluate([], use_llm=False)
        assert result.aggregate_score == 1.0
        assert result.evaluations == []
        assert result.fallback is True

    def test_heuristic_path_when_use_llm_false(self):
        judge = SemanticJudge()
        reports = [_make_report(), _make_report()]
        result = judge.evaluate(reports, use_llm=False)
        assert result.provider == "heuristic"
        assert result.fallback is True
        assert len(result.evaluations) == 2

    def test_aggregate_score_is_mean_of_evaluations(self):
        judge = SemanticJudge()
        reports = [_make_report(diff="status mismatch: expected=400, actual=200")]
        result = judge.evaluate(reports, use_llm=False)
        if result.evaluations:
            expected_agg = sum(e.quality_score for e in result.evaluations) / len(result.evaluations)
            assert abs(result.aggregate_score - expected_agg) < 0.01

    def test_llm_path_falls_back_on_error(self):
        judge = SemanticJudge()
        reports = [_make_report()]
        with patch("cherenkov.substrate.router.SubstrateRouter") as mock_router:
            mock_router.side_effect = ImportError("substrate unavailable")
            result = judge.evaluate(reports, use_llm=True)
        # Should fall back to heuristic
        assert result.fallback is True

    def test_duration_ms_is_positive(self):
        judge = SemanticJudge()
        reports = [_make_report()]
        result = judge.evaluate(reports, use_llm=False)
        assert result.duration_ms >= 0
