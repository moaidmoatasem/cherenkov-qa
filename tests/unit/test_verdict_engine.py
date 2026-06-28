"""Tests for cherenkov/verdict/engine.py — VerdictEngine."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceReport,
    Severity,
    StageMeta,
    Status,
)
from cherenkov.verdict.engine import VerdictEngine, _dim_name
from cherenkov.verdict.models import (
    OverallVerdict,
    RichVerdict,
    VerdictDimension,
    VerdictGrade,
)


def _make_report(severity: Severity = Severity.MEDIUM) -> DivergenceReport:
    return DivergenceReport(
        id=str(uuid.uuid4()),
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a="spec says 400",
        claim_b="impl returns 200",
        evidence=DivergenceEvidence(
            request_summary="GET /test → 200 (10ms)",
            response_actual="200",
            response_expected="400",
            diff="status mismatch: expected=400, actual=200",
        ),
        repro_steps=["Send GET /test", "Expect 400"],
        severity=severity,
        status=Status.OK,
        metadata=StageMeta(stage="test"),
    )


# ── _dim_name helper ──────────────────────────────────────────────────────────

class TestDimName:
    def test_coverage_maps_correctly(self):
        assert _dim_name("coverage") == "spec_coverage"

    def test_mutation_maps_correctly(self):
        assert _dim_name("mutation") == "mutation_oracle"

    def test_semantic_maps_correctly(self):
        assert _dim_name("semantic") == "semantic_judge"

    def test_traffic_maps_correctly(self):
        assert _dim_name("traffic") == "traffic_capture"

    def test_unknown_key_passes_through(self):
        assert _dim_name("unknown_key") == "unknown_key"


# ── VerdictEngine construction ────────────────────────────────────────────────

class TestVerdictEngineInit:
    def test_default_settings(self):
        engine = VerdictEngine(base_url="http://test")
        assert engine.base_url == "http://test"
        assert engine.use_llm is False
        assert engine.run_mutation_oracle is True
        assert engine.run_semantic_judge is True
        assert engine.run_traffic_capture is True

    def test_custom_settings(self):
        engine = VerdictEngine(
            base_url="http://x",
            use_llm=True,
            run_mutation_oracle=False,
            max_workers=2,
        )
        assert engine.use_llm is True
        assert engine.run_mutation_oracle is False
        assert engine.max_workers == 2


# ── _run_divergence_probe ─────────────────────────────────────────────────────

class TestRunDivergenceProbe:
    def test_no_divergences_yields_high_score(self):
        engine = VerdictEngine(base_url="http://test")
        with patch("cherenkov.divergence.proof_run.run_proof", return_value=[]):
            dim, reports = engine._run_divergence_probe()
        assert dim.score == 1.0
        assert dim.passed is True
        assert reports == []

    def test_high_severity_divergence_penalises_score(self):
        engine = VerdictEngine(base_url="http://test")
        with patch(
            "cherenkov.divergence.proof_run.run_proof",
            return_value=[_make_report(Severity.HIGH)],
        ):
            dim, reports = engine._run_divergence_probe()
        assert dim.score < 1.0
        assert len(reports) == 1

    def test_critical_divergence_fails_gate(self):
        engine = VerdictEngine(base_url="http://test")
        reports = [_make_report(Severity.CRITICAL)] * 3
        with patch("cherenkov.divergence.proof_run.run_proof", return_value=reports):
            dim, _ = engine._run_divergence_probe()
        assert dim.score < 0.6
        assert dim.passed is False

    def test_probe_exception_yields_zero_score(self):
        engine = VerdictEngine(base_url="http://test")
        with patch("cherenkov.divergence.proof_run.run_proof", side_effect=RuntimeError("conn refused")):
            dim, reports = engine._run_divergence_probe()
        assert dim.score == 0.0
        assert reports == []
        assert dim.passed is False


# ── _run_coverage_analyzer ────────────────────────────────────────────────────

class TestRunCoverageAnalyzer:
    def test_full_coverage_passes(self):
        engine = VerdictEngine(base_url="http://test")
        mock_cov = MagicMock()
        mock_cov.coverage_pct = 100.0
        with patch("cherenkov.divergence.coverage.compute_coverage", return_value=mock_cov):
            dim, pct = engine._run_coverage_analyzer([])
        assert dim.passed is True
        assert pct == 100.0

    def test_low_coverage_fails_gate(self):
        engine = VerdictEngine(base_url="http://test")
        mock_cov = MagicMock()
        mock_cov.coverage_pct = 30.0
        with patch("cherenkov.divergence.coverage.compute_coverage", return_value=mock_cov):
            dim, pct = engine._run_coverage_analyzer([])
        assert dim.passed is False
        assert pct == 30.0
        assert any("30%" in f or "30" in f for f in dim.findings)


# ── _run_mutation_oracle ───────────────────────────────────────────────────────

class TestRunMutationOracle:
    def test_perfect_oracle_passes(self):
        engine = VerdictEngine(base_url="http://test")
        mock_oracle_report = MagicMock()
        mock_oracle_report.score = 1.0
        mock_oracle_report.detected = 4
        mock_oracle_report.mutations_run = 4
        mock_oracle_report.results = []
        mock_oracle = MagicMock()
        mock_oracle.run.return_value = mock_oracle_report
        with patch("cherenkov.verdict.mutation_oracle.MutationOracle", return_value=mock_oracle):
            dim, score = engine._run_mutation_oracle()
        assert dim.passed is True
        assert score == 1.0

    def test_low_score_fails_gate(self):
        engine = VerdictEngine(base_url="http://test")
        mock_oracle_report = MagicMock()
        mock_oracle_report.score = 0.5
        mock_oracle_report.detected = 2
        mock_oracle_report.mutations_run = 4
        mock_oracle_report.results = []
        mock_oracle = MagicMock()
        mock_oracle.run.return_value = mock_oracle_report
        with patch("cherenkov.verdict.mutation_oracle.MutationOracle", return_value=mock_oracle):
            dim, score = engine._run_mutation_oracle()
        assert dim.passed is False
        assert score == 0.5


# ── _run_semantic_judge ────────────────────────────────────────────────────────

class TestRunSemanticJudge:
    def test_high_quality_passes(self):
        engine = VerdictEngine(base_url="http://test")
        mock_judge_report = MagicMock()
        mock_judge_report.aggregate_score = 0.9
        mock_judge_report.provider = "heuristic"
        mock_judge_report.evaluations = []
        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = mock_judge_report
        with patch("cherenkov.verdict.semantic_judge.SemanticJudge", return_value=mock_judge):
            dim, score = engine._run_semantic_judge([])
        assert dim.passed is True
        assert score == 0.9


# ── VerdictEngine.run (integration, mocked) ───────────────────────────────────

class TestVerdictEngineRun:
    def test_run_returns_rich_verdict(self):
        engine = VerdictEngine(
            base_url="http://test",
            run_mutation_oracle=False,
            run_semantic_judge=False,
            run_traffic_capture=False,
        )
        with patch("cherenkov.divergence.proof_run.run_proof", return_value=[]), \
             patch("cherenkov.divergence.coverage.compute_coverage", return_value=MagicMock(coverage_pct=80.0)):
            result = engine.run()
        assert isinstance(result, RichVerdict)
        assert result.target_url == "http://test"

    def test_run_with_divergences_marks_divergent(self):
        engine = VerdictEngine(
            base_url="http://test",
            run_mutation_oracle=False,
            run_semantic_judge=False,
            run_traffic_capture=False,
        )
        reports = [_make_report(Severity.HIGH)]
        with patch("cherenkov.divergence.proof_run.run_proof", return_value=reports), \
             patch("cherenkov.divergence.coverage.compute_coverage", return_value=MagicMock(coverage_pct=60.0)):
            result = engine.run()
        assert result.overall == OverallVerdict.DIVERGENT

    def test_run_dimensions_include_probe_and_coverage(self):
        engine = VerdictEngine(
            base_url="http://test",
            run_mutation_oracle=False,
            run_semantic_judge=False,
            run_traffic_capture=False,
        )
        with patch("cherenkov.divergence.proof_run.run_proof", return_value=[]), \
             patch("cherenkov.divergence.coverage.compute_coverage", return_value=MagicMock(coverage_pct=75.0)):
            result = engine.run()
        names = {d.name for d in result.dimensions}
        assert "divergence_probe" in names
        assert "spec_coverage" in names

    def test_run_duration_ms_is_positive(self):
        engine = VerdictEngine(
            base_url="http://test",
            run_mutation_oracle=False,
            run_semantic_judge=False,
            run_traffic_capture=False,
        )
        with patch("cherenkov.divergence.proof_run.run_proof", return_value=[]), \
             patch("cherenkov.divergence.coverage.compute_coverage", return_value=MagicMock(coverage_pct=80.0)):
            result = engine.run()
        assert result.duration_ms >= 0
