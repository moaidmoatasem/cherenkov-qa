from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from cherenkov.evals.core import (
    EvalMetric,
    EvalReport,
    EvalResult,
    EvalSample,
    EvalScore,
    EvalStatus,
)
from cherenkov.evals.judge import _build_judge_prompt, _parse_score
from cherenkov.evals.store import EvalStore


class TestEvalCore(unittest.TestCase):
    def test_eval_score_passing(self):
        s = _parse_score("faithfulness", {"score": 0.95, "detail": "good", "status": "pass"})
        self.assertEqual(s.metric, EvalMetric.FAITHFULNESS)
        self.assertEqual(s.score, 0.95)
        self.assertEqual(s.status, EvalStatus.PASS)

    def test_eval_score_failing(self):
        s = _parse_score("hallucination", {"score": 0.3, "detail": "hallucinates", "status": "fail"})
        self.assertEqual(s.metric, EvalMetric.HALLUCINATION)
        self.assertEqual(s.score, 0.3)
        self.assertEqual(s.status, EvalStatus.FAIL)

    def test_eval_score_edge(self):
        s = _parse_score("assertion_quality", {"score": 0.5, "detail": "basic", "status": "pass"})
        self.assertEqual(s.status, EvalStatus.WARN)

    def test_build_judge_prompt(self):
        sample = EvalSample(
            scenario_id="happy_path",
            endpoint="/api/users",
            method="POST",
            expected_status=201,
            test_code="test('create', async () => { ... })",
            spec_summary="POST /api/users returns 201 with user object",
        )
        prompt = _build_judge_prompt(sample)
        self.assertIn("POST /api/users", prompt)
        self.assertIn("201", prompt)
        self.assertIn("happy_path", prompt)

    def test_eval_result_passed(self):
        sample = EvalSample(scenario_id="t1", endpoint="/x", method="GET", expected_status=200, test_code="", spec_summary="")
        scores = [EvalScore(metric=EvalMetric.FAITHFULNESS, score=0.9, status=EvalStatus.PASS, detail="ok")]
        r = EvalResult(sample=sample, scores=scores, duration_ms=100)
        self.assertTrue(r.passed())

    def test_eval_result_failed(self):
        sample = EvalSample(scenario_id="t1", endpoint="/x", method="GET", expected_status=200, test_code="", spec_summary="")
        scores = [EvalScore(metric=EvalMetric.FAITHFULNESS, score=0.3, status=EvalStatus.FAIL, detail="bad")]
        r = EvalResult(sample=sample, scores=scores, duration_ms=100)
        self.assertFalse(r.passed())

    def test_eval_report_pass_rate(self):
        sample = EvalSample(scenario_id="t1", endpoint="/x", method="GET", expected_status=200, test_code="", spec_summary="")
        r1 = EvalResult(sample=sample, scores=[EvalScore(metric=EvalMetric.FAITHFULNESS, score=0.9, status=EvalStatus.PASS, detail="ok")], duration_ms=10)
        r2 = EvalResult(sample=sample, scores=[EvalScore(metric=EvalMetric.FAITHFULNESS, score=0.3, status=EvalStatus.FAIL, detail="bad")], duration_ms=10)
        report = EvalReport(results=[r1, r2], model="test", eval_timestamp="now")
        self.assertEqual(report.pass_rate(), 0.5)

    def test_eval_report_metric_averages(self):
        sample = EvalSample(scenario_id="t1", endpoint="/x", method="GET", expected_status=200, test_code="", spec_summary="")
        s1 = EvalScore(metric=EvalMetric.FAITHFULNESS, score=0.9, status=EvalStatus.PASS, detail="ok")
        s2 = EvalScore(metric=EvalMetric.FAITHFULNESS, score=0.7, status=EvalStatus.PASS, detail="ok")
        r = EvalResult(sample=sample, scores=[s1, s2], duration_ms=10)
        report = EvalReport(results=[r], model="test", eval_timestamp="now")
        avgs = report.metric_averages()
        self.assertAlmostEqual(avgs["faithfulness"], 0.8)

    def test_eval_report_to_dict(self):
        sample = EvalSample(scenario_id="t1", endpoint="/x", method="GET", expected_status=200, test_code="", spec_summary="")
        s = EvalScore(metric=EvalMetric.FAITHFULNESS, score=0.9, status=EvalStatus.PASS, detail="ok")
        r = EvalResult(sample=sample, scores=[s], duration_ms=10)
        report = EvalReport(results=[r], model="test", eval_timestamp="now")
        d = report.to_dict()
        self.assertIn("pass_rate", d)
        self.assertIn("metric_averages", d)
        self.assertEqual(d["total_scenarios"], 1)


class TestEvalStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.tmp.name)
        self.tmp.close()
        self.store = EvalStore(db_path=self.db_path)

    def tearDown(self):
        if hasattr(self, "store"):
            pass
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except Exception:
                pass

    def _make_report(self, pass_rate: float = 1.0) -> EvalReport:
        sample = EvalSample(scenario_id="t1", endpoint="/x", method="GET", expected_status=200, test_code="", spec_summary="")
        status = EvalStatus.PASS if pass_rate >= 0.7 else EvalStatus.FAIL
        s = EvalScore(metric=EvalMetric.FAITHFULNESS, score=pass_rate, status=status, detail="ok")
        r = EvalResult(sample=sample, scores=[s], duration_ms=10)
        passed = status == EvalStatus.PASS
        return EvalReport(results=[r], model="test", eval_timestamp="now")

    def test_save_and_latest(self):
        report = self._make_report(0.95)
        self.store.save(report)
        latest = self.store.latest()
        self.assertIsNotNone(latest)
        self.assertEqual(latest["pass_rate"], 1.0)

    def test_save_and_history(self):
        r1 = self._make_report(0.95)
        r2 = self._make_report(0.5)
        self.store.save(r1)
        self.store.save(r2)
        history = self.store.history(limit=10)
        self.assertEqual(len(history), 2)
        pass_rates = [h["pass_rate"] for h in history]
        self.assertIn(0.0, pass_rates)
        self.assertIn(1.0, pass_rates)

    def test_empty_history(self):
        history = self.store.history(limit=10)
        self.assertEqual(history, [])

    def test_empty_latest(self):
        self.assertIsNone(self.store.latest())
