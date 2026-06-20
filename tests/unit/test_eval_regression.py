"""Unit tests for cherenkov/evals/regression.py — regression detector."""

import json
import tempfile
import unittest
from pathlib import Path

from cherenkov.evals.core import (
    EvalMetric, EvalReport, EvalResult, EvalSample, EvalScore, EvalStatus
)
from cherenkov.evals.regression import RegressionGuard, RegressionError


def _make_report(pass_rate_target: float, metric_score: float = 0.90) -> EvalReport:
    """Build a synthetic EvalReport with a controlled pass rate."""
    n_total = 10
    n_pass = round(pass_rate_target * n_total)
    results = []
    for i in range(n_total):
        passed = i < n_pass
        score = metric_score if passed else max(0.0, metric_score - 0.3)
        status = EvalStatus.PASS if passed else EvalStatus.FAIL
        sample = EvalSample(
            scenario_id=f"s{i}",
            endpoint="/items",
            method="GET",
            expected_status=200,
            test_code="test_code",
            spec_summary="",
        )
        scores = [
            EvalScore(metric=EvalMetric.FAITHFULNESS, score=score, status=status, detail=""),
            EvalScore(metric=EvalMetric.ASSERTION_QUALITY, score=score, status=status, detail=""),
        ]
        results.append(EvalResult(sample=sample, scores=scores, duration_ms=10))
    return EvalReport(results=results, model="test-model", eval_timestamp="2026-06-21T00:00:00Z")


class TestRegressionGuardNoBaseline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.baseline_path = Path(self.tmp) / "baseline.json"

    def test_no_baseline_returns_no_findings(self):
        guard = RegressionGuard(baseline_path=self.baseline_path)
        report = _make_report(pass_rate_target=0.70)
        findings = guard.check(report)
        self.assertEqual(findings, [])

    def test_no_baseline_does_not_raise(self):
        guard = RegressionGuard(baseline_path=self.baseline_path)
        report = _make_report(pass_rate_target=0.70)
        guard.assert_no_regression(report)  # should not raise


class TestRegressionGuardWithBaseline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.baseline_path = Path(self.tmp) / "baseline.json"

    def _save_baseline(self, metrics: dict) -> None:
        self.baseline_path.write_text(
            json.dumps({"metrics": metrics, "model": "test", "timestamp": ""}),
            encoding="utf-8",
        )

    def test_no_regression_when_on_par(self):
        self._save_baseline({"pass_rate": 0.80, "faithfulness": 0.85})
        guard = RegressionGuard(baseline_path=self.baseline_path)
        report = _make_report(pass_rate_target=0.80, metric_score=0.90)
        findings = guard.check(report)
        self.assertEqual(findings, [])

    def test_small_drop_within_tolerance_not_flagged(self):
        self._save_baseline({"pass_rate": 0.90})
        guard = RegressionGuard(baseline_path=self.baseline_path, tolerance={"pass_rate": 0.05})
        report = _make_report(pass_rate_target=0.86)
        findings = guard.check(report)
        self.assertEqual(findings, [])

    def test_large_drop_detected(self):
        self._save_baseline({"pass_rate": 0.90})
        guard = RegressionGuard(baseline_path=self.baseline_path, tolerance={"pass_rate": 0.05})
        report = _make_report(pass_rate_target=0.70)
        findings = guard.check(report)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].metric, "pass_rate")
        self.assertLess(findings[0].delta, 0)
        self.assertGreater(findings[0].exceeded_by, 0)

    def test_assert_raises_on_regression(self):
        self._save_baseline({"pass_rate": 0.90})
        guard = RegressionGuard(baseline_path=self.baseline_path, tolerance={"pass_rate": 0.05})
        report = _make_report(pass_rate_target=0.70)
        with self.assertRaises(RegressionError) as ctx:
            guard.assert_no_regression(report)
        self.assertIn("pass_rate", str(ctx.exception))

    def test_improvement_never_flagged(self):
        self._save_baseline({"pass_rate": 0.70})
        guard = RegressionGuard(baseline_path=self.baseline_path)
        report = _make_report(pass_rate_target=0.95)
        findings = guard.check(report)
        self.assertEqual(findings, [])


class TestSaveAndLoadBaseline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.baseline_path = Path(self.tmp) / "baseline.json"

    def test_round_trip(self):
        guard = RegressionGuard(baseline_path=self.baseline_path)
        report = _make_report(pass_rate_target=0.90)
        guard.save_baseline(report)
        self.assertTrue(self.baseline_path.exists())
        loaded = guard.load_baseline()
        self.assertIn("pass_rate", loaded)
        self.assertAlmostEqual(loaded["pass_rate"], 0.90, places=1)

    def test_after_save_no_regression_on_same_report(self):
        guard = RegressionGuard(baseline_path=self.baseline_path)
        report = _make_report(pass_rate_target=0.90)
        guard.save_baseline(report)
        findings = guard.check(report)
        self.assertEqual(findings, [])


class TestEvalReportFromDict(unittest.TestCase):
    def test_from_dict_round_trip(self):
        report = _make_report(0.80)
        d = report.to_dict()
        restored = EvalReport.from_dict(d)
        self.assertAlmostEqual(restored.pass_rate(), report.pass_rate(), places=1)
        self.assertEqual(restored.model, report.model)

    def test_total_scenarios(self):
        report = _make_report(1.0)
        self.assertEqual(report.total_scenarios(), 10)


if __name__ == "__main__":
    unittest.main()
