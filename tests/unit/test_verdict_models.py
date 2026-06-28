"""Tests for cherenkov/verdict/models.py — RichVerdict contracts."""

from __future__ import annotations

import pytest

from cherenkov.verdict.models import (
    ActionableFinding,
    OverallVerdict,
    RichVerdict,
    RiskFlag,
    VerdictDimension,
    VerdictGrade,
    _estimate_fix_time,
    assemble_verdict,
    score_to_grade,
)


# ── score_to_grade ─────────────────────────────────────────────────────────────

class TestScoreToGrade:
    def test_perfect_score_is_A(self):
        assert score_to_grade(1.0) == VerdictGrade.A

    def test_ninety_pct_is_A(self):
        assert score_to_grade(0.90) == VerdictGrade.A

    def test_eighty_pct_is_B(self):
        assert score_to_grade(0.80) == VerdictGrade.B

    def test_seventy_five_pct_is_B(self):
        assert score_to_grade(0.75) == VerdictGrade.B

    def test_sixty_pct_is_C(self):
        assert score_to_grade(0.60) == VerdictGrade.C

    def test_forty_pct_is_D(self):
        assert score_to_grade(0.40) == VerdictGrade.D

    def test_zero_is_F(self):
        assert score_to_grade(0.0) == VerdictGrade.F

    def test_below_forty_is_F(self):
        assert score_to_grade(0.39) == VerdictGrade.F

    def test_boundary_75_is_B(self):
        assert score_to_grade(0.749) == VerdictGrade.C


# ── _estimate_fix_time ─────────────────────────────────────────────────────────

class TestEstimateFixTime:
    def test_empty_findings_is_none_needed(self):
        assert _estimate_fix_time([]) == "none needed"

    def test_single_low_finding(self):
        f = ActionableFinding(
            rank=1, severity="low", divergence_class="D1", endpoint="/x",
            summary="test", remediation="fix", estimated_fix_minutes=15,
        )
        assert "min" in _estimate_fix_time([f])

    def test_many_critical_findings_is_sprint(self):
        findings = [
            ActionableFinding(
                rank=i, severity="critical", divergence_class="D1", endpoint="/x",
                summary="test", remediation="fix", estimated_fix_minutes=120,
            )
            for i in range(1, 6)
        ]
        result = _estimate_fix_time(findings)
        assert "sprint" in result or "h" in result


# ── VerdictDimension ───────────────────────────────────────────────────────────

class TestVerdictDimension:
    def test_basic_construction(self):
        dim = VerdictDimension(
            name="divergence_probe",
            score=0.85,
            grade=VerdictGrade.B,
            passed=True,
        )
        assert dim.name == "divergence_probe"
        assert dim.score == 0.85
        assert dim.passed is True

    def test_findings_default_empty(self):
        dim = VerdictDimension(name="x", score=0.5, grade=VerdictGrade.C, passed=False)
        assert dim.findings == []


# ── assemble_verdict ───────────────────────────────────────────────────────────

def _make_dim(name: str, score: float, passed: bool) -> VerdictDimension:
    return VerdictDimension(
        name=name,
        score=score,
        grade=score_to_grade(score),
        passed=passed,
    )


class TestAssembleVerdict:
    def test_no_divergences_grades_high(self):
        dims = [
            _make_dim("divergence_probe", 1.0, True),
            _make_dim("spec_coverage", 0.95, True),
        ]
        v = assemble_verdict(
            target_url="http://localhost",
            spec_source="test",
            dimensions=dims,
            divergence_reports=[],
            coverage_pct=95.0,
            mutation_score=1.0,
            semantic_score=1.0,
            captured_fixtures=3,
            duration_ms=500,
        )
        assert v.grade in (VerdictGrade.A, VerdictGrade.B)
        assert v.overall == OverallVerdict.CERTIFIED
        assert v.divergence_count == 0
        assert v.captured_fixtures == 3

    def test_divergences_yield_divergent_verdict(self, mock_report):
        dims = [_make_dim("divergence_probe", 0.5, False)]
        v = assemble_verdict(
            target_url="http://localhost",
            spec_source="test",
            dimensions=dims,
            divergence_reports=[mock_report],
            coverage_pct=60.0,
            mutation_score=None,
            semantic_score=None,
            captured_fixtures=0,
            duration_ms=1000,
        )
        assert v.overall == OverallVerdict.DIVERGENT
        assert v.divergence_count == 1

    def test_low_coverage_sets_risk_flag(self):
        dims = [_make_dim("divergence_probe", 1.0, True)]
        v = assemble_verdict(
            target_url="http://x",
            spec_source="test",
            dimensions=dims,
            divergence_reports=[],
            coverage_pct=30.0,
            mutation_score=None,
            semantic_score=None,
            captured_fixtures=0,
            duration_ms=0,
        )
        assert RiskFlag.LOW_COVERAGE in v.risk_flags

    def test_low_mutation_score_sets_vacuous_flag(self):
        dims = [_make_dim("mutation_oracle", 0.5, False)]
        v = assemble_verdict(
            target_url="http://x",
            spec_source="test",
            dimensions=dims,
            divergence_reports=[],
            coverage_pct=80.0,
            mutation_score=0.4,
            semantic_score=None,
            captured_fixtures=0,
            duration_ms=0,
        )
        assert RiskFlag.VACUOUS_ASSERTIONS in v.risk_flags

    def test_confidence_is_in_unit_range(self):
        dims = [_make_dim("divergence_probe", 0.8, True)]
        v = assemble_verdict(
            target_url="http://x",
            spec_source="test",
            dimensions=dims,
            divergence_reports=[],
            coverage_pct=80.0,
            mutation_score=0.9,
            semantic_score=0.85,
            captured_fixtures=0,
            duration_ms=0,
        )
        assert 0.0 <= v.confidence <= 1.0

    def test_run_id_is_set(self):
        dims = [_make_dim("divergence_probe", 1.0, True)]
        v = assemble_verdict(
            target_url="http://x", spec_source="test", dimensions=dims,
            divergence_reports=[], coverage_pct=100.0, mutation_score=None,
            semantic_score=None, captured_fixtures=0, duration_ms=0,
        )
        assert v.run_id


# ── RichVerdict.render ─────────────────────────────────────────────────────────

class TestRichVerdictRender:
    def test_render_contains_target_url(self, basic_rich_verdict):
        rendered = basic_rich_verdict.render()
        assert "http://test-target" in rendered

    def test_render_contains_grade(self, basic_rich_verdict):
        rendered = basic_rich_verdict.render()
        assert basic_rich_verdict.grade.value in rendered

    def test_render_contains_overall_verdict(self, basic_rich_verdict):
        rendered = basic_rich_verdict.render()
        assert basic_rich_verdict.overall.value in rendered

    def test_render_shows_risk_flags(self):
        v = RichVerdict(
            target_url="http://x",
            overall=OverallVerdict.SUSPECT,
            grade=VerdictGrade.C,
            confidence=0.6,
            risk_flags=[RiskFlag.SCHEMA_DRIFT, RiskFlag.LOW_COVERAGE],
        )
        rendered = v.render()
        assert "SCHEMA_DRIFT" in rendered or "LOW_COVERAGE" in rendered

    def test_render_shows_top_findings(self):
        finding = ActionableFinding(
            rank=1, severity="high", divergence_class="D1_spec_code",
            endpoint="GET /pets", summary="enum not enforced",
            remediation="Add server-side validation",
        )
        v = RichVerdict(
            target_url="http://x",
            overall=OverallVerdict.DIVERGENT,
            grade=VerdictGrade.D,
            confidence=0.7,
            top_findings=[finding],
        )
        rendered = v.render()
        assert "HIGH" in rendered
        assert "Add server-side" in rendered

    def test_render_shows_dimensions(self):
        v = RichVerdict(
            target_url="http://x",
            overall=OverallVerdict.DIVERGENT,
            grade=VerdictGrade.B,
            confidence=0.8,
            dimensions=[
                VerdictDimension(
                    name="divergence_probe", score=0.8,
                    grade=VerdictGrade.B, passed=True,
                )
            ],
        )
        rendered = v.render()
        assert "divergence_probe" in rendered

    def test_render_is_box_shaped(self, basic_rich_verdict):
        rendered = basic_rich_verdict.render()
        lines = rendered.split("\n")
        assert lines[0].startswith("╔")
        assert lines[-1].startswith("╚")


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_report():
    """Minimal DivergenceReport-like object."""
    from unittest.mock import MagicMock
    from cherenkov.core.contracts import Severity, DivergenceClass

    r = MagicMock()
    r.severity = Severity.HIGH
    r.divergence_class = DivergenceClass.D1_SPEC_CODE
    r.endpoint = "GET /pet/findByStatus"
    r.claim_a = "spec: status param must be enum(available|pending|sold)"
    r.claim_b = "implementation accepts any string"
    return r


@pytest.fixture
def basic_rich_verdict():
    return RichVerdict(
        target_url="http://test-target",
        overall=OverallVerdict.DIVERGENT,
        grade=VerdictGrade.B,
        confidence=0.82,
        dimensions=[
            VerdictDimension(
                name="divergence_probe", score=0.7,
                grade=VerdictGrade.C, passed=False,
            )
        ],
        divergence_count=2,
        coverage_pct=75.0,
        time_to_fix_estimate="~2h",
    )
