"""tests/evals/test_review_integrity.py — CI quality gate for the REVIEW stage.

Verifies that the 6-gate REVIEW stage:
  1. Approves correct spec-derived tests (high quality score)
  2. Catches weakened assertions (Gate 4 fails)
  3. Catches deleted body checks (Gate 4 fails)
  4. Correctly scores the golden bench fixtures

These tests run OFFLINE — no LLM, no Docker, no network.
Gate 5 (tsc) and Gate 6 (prism-dryrun) are automatically skipped when
the required infra is absent; the tests assert on the static gates only.

References:
  Yuan et al. FSE 2024 — ChatGPT generated tests: 39% compile, 22.3% pass
  Cherenkov target     — gate quality score ≥ 85% on correct tests
"""
from __future__ import annotations

import os
import pytest

from cherenkov.core.contracts import GenerateOutput, StageMeta, Status
from cherenkov.core.errors import LoggerConfig
from cherenkov.stages.review import ReviewStage

@pytest.fixture(autouse=True)
def _suppress_logging():
    LoggerConfig.suppress_stderr = True
    yield
    LoggerConfig.suppress_stderr = False

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
_DEMO_DIR = os.path.join(_REPO_ROOT, "demos", "catch-the-ai-cheating", "fixtures")
_GOLDEN_DIR = os.path.join(_REPO_ROOT, "bench", "fixtures", "golden_tests")
_SPEC_PATH = os.path.join(_REPO_ROOT, "stub", "openapi_3_1.yaml")


def _load(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _review(code: str, scenario_id: str) -> "ReviewOutput":  # noqa: F821
    out = GenerateOutput(
        scenario_id=scenario_id,
        test_code=code,
        endpoint="/test",
        method="POST",
        status=Status.OK,
        metadata=StageMeta(stage="GENERATE"),
    )
    stage = ReviewStage(run_id=f"eval-{scenario_id}")
    return stage.run(out, spec_path=_SPEC_PATH)


def _gate(result, name: str):
    for g in result.gates:
        if g.gate == name:
            return g
    return None


def _static_gates_only(result) -> list:
    """Gates 1–4 — always evaluated without external infra."""
    return [g for g in result.gates if g.gate in ("syntax", "structure", "ast", "assertion")]


# ── Demo fixtures (catch-the-ai-cheating) ─────────────────────────────────────


class TestDemoFixtures:
    """REVIEW stage must classify the four demo cheat fixtures correctly."""

    def test_correct_test_passes_static_gates(self):
        path = os.path.join(_DEMO_DIR, "correct_test.spec.ts")
        result = _review(_load(path), "demo_correct")
        for gate in _static_gates_only(result):
            assert gate.passed or gate.skipped, (
                f"Gate [{gate.gate}] should pass on a correct test — got: {gate.detail}"
            )

    def test_correct_test_quality_score_high(self):
        path = os.path.join(_DEMO_DIR, "correct_test.spec.ts")
        result = _review(_load(path), "demo_correct_q")
        static_gates = _static_gates_only(result)
        static_pass = sum(1 for g in static_gates if g.passed)
        static_total = sum(1 for g in static_gates if not g.skipped)
        assert static_total > 0, "No static gates evaluated"
        rate = static_pass / static_total
        assert rate >= 1.0, (
            f"All static gates should pass on correct test; got {rate:.0%} "
            f"({static_pass}/{static_total})"
        )

    def test_weakened_assertion_caught_by_gate4(self):
        path = os.path.join(_DEMO_DIR, "cheat_weakened_assertion.spec.ts")
        result = _review(_load(path), "demo_weakened")
        gate4 = _gate(result, "assertion")
        assert gate4 is not None, "Gate 4 (assertion) must be present"
        assert not gate4.passed, (
            "Gate 4 must FAIL on weakened assertion (toBeLessThan instead of toBe)"
        )

    def test_deleted_check_caught_by_gate4(self):
        path = os.path.join(_DEMO_DIR, "cheat_deleted_check.spec.ts")
        result = _review(_load(path), "demo_deleted")
        gate4 = _gate(result, "assertion")
        assert gate4 is not None, "Gate 4 (assertion) must be present"
        assert not gate4.passed, (
            "Gate 4 must FAIL when body shape assertions are deleted"
        )

    def test_weakened_verdict_not_auto_approve(self):
        path = os.path.join(_DEMO_DIR, "cheat_weakened_assertion.spec.ts")
        result = _review(_load(path), "demo_weakened_v")
        assert result.verdict.value != "AUTO_APPROVE", (
            f"Weakened assertion must not AUTO_APPROVE; got {result.verdict.value}"
        )

    def test_deleted_check_verdict_not_auto_approve(self):
        path = os.path.join(_DEMO_DIR, "cheat_deleted_check.spec.ts")
        result = _review(_load(path), "demo_deleted_v")
        assert result.verdict.value != "AUTO_APPROVE", (
            f"Deleted body check must not AUTO_APPROVE; got {result.verdict.value}"
        )

    def test_hallucinated_oracle_passes_static_gates(self):
        """Gate 6 (Prism) catches hallucinated oracles; static gates pass.
        When Docker is absent, Gate 6 is skipped — that is expected and honest."""
        path = os.path.join(_DEMO_DIR, "cheat_hallucinated_oracle.spec.ts")
        result = _review(_load(path), "demo_hallucinated")
        for gate in _static_gates_only(result):
            assert gate.passed or gate.skipped, (
                f"Gate [{gate.gate}] should pass on hallucinated oracle test "
                f"(structurally valid; only Prism gate catches it) — got: {gate.detail}"
            )


# ── Golden bench fixtures ─────────────────────────────────────────────────────


class TestGoldenFixtures:
    """Bench golden fixtures must produce the expected gate outcomes."""

    def test_correct_petstore_passes_static_gates(self):
        path = os.path.join(_GOLDEN_DIR, "correct_petstore.spec.ts")
        result = _review(_load(path), "golden_correct")
        for gate in _static_gates_only(result):
            assert gate.passed or gate.skipped, (
                f"Gate [{gate.gate}] should pass on correct Petstore test — {gate.detail}"
            )

    def test_weakened_assertion_petstore_caught(self):
        path = os.path.join(_GOLDEN_DIR, "weakened_assertion_petstore.spec.ts")
        result = _review(_load(path), "golden_weakened")
        gate4 = _gate(result, "assertion")
        assert gate4 is not None
        assert not gate4.passed, "Gate 4 must catch weakened assertion in Petstore fixture"

    def test_deleted_check_petstore_caught(self):
        path = os.path.join(_GOLDEN_DIR, "deleted_check_petstore.spec.ts")
        result = _review(_load(path), "golden_deleted")
        gate4 = _gate(result, "assertion")
        assert gate4 is not None
        assert not gate4.passed, "Gate 4 must catch missing body check in Petstore fixture"


# ── Bench runner smoke test ───────────────────────────────────────────────────


class TestBenchRunner:
    """cherenkov.bench runner produces plausible aggregate metrics."""

    def test_bench_golden_dir_runs(self):
        from cherenkov.bench.runner import bench_directory
        result = bench_directory(_GOLDEN_DIR, spec_path=_SPEC_PATH)
        assert result.scenario_count == 3, (
            f"Expected 3 golden fixtures, got {result.scenario_count}"
        )
        assert result.avg_quality_score >= 0.0
        assert "assertion" in result.gate_summaries
        assert "auto_approve" in result.verdict_distribution

    def test_bench_correct_fixture_quality(self):
        """The correct fixture should pull avg quality score above 0 (static gates pass)."""
        from cherenkov.bench.runner import bench_directory
        correct_only = os.path.join(_GOLDEN_DIR)
        result = bench_directory(correct_only, spec_path=_SPEC_PATH)
        assert result.avg_quality_score > 0.0

    def test_bench_report_populated(self):
        from cherenkov.bench.runner import run_bench
        from cherenkov.bench.metrics import BenchReport
        report = run_bench([_GOLDEN_DIR], spec_path=_SPEC_PATH)
        assert isinstance(report, BenchReport)
        assert report.total_scenarios == 3
        assert report.overall_quality_score >= 0.0
