from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest import mock

from cherenkov.execution.k6_runner import K6Runner


class TestK6Runner(unittest.TestCase):
    def test_export_k6_script_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = K6Runner(run_id="test")
            runner.tests_dir = tmpdir
            runner.k6_script_path = os.path.join(tmpdir, "k6_perf.js")
            code = runner.export_k6_script("http://localhost:8000")
            self.assertIn("http.post", code)
            self.assertTrue(os.path.exists(runner.k6_script_path))

    def test_run_k6_validation_degraded_when_k6_missing(self):
        runner = K6Runner(run_id="test")
        with mock.patch("cherenkov.execution.k6_runner.shutil.which", return_value=None):
            report = runner.run_k6_validation("http://localhost:8000")
        self.assertEqual(report["status"], "degraded")
        self.assertIn("k6 binary is not installed", report["message"])

    def test_run_k6_validation_parses_metrics(self):
        runner = K6Runner(run_id="test")
        fake_stdout = (
            "http_req_duration....................: avg=123.45ms min=10ms med=100ms max=500ms p(95)=250ms\n"
            "http_reqs............................: 100 50.0000/s\n"
            "http_req_failed......................: 0.00% 0 out of 100\n"
        )
        fake_process = mock.Mock(
            returncode=0,
            stdout=fake_stdout,
            stderr="",
        )
        with mock.patch("cherenkov.execution.k6_runner.shutil.which", return_value="/usr/bin/k6"):
            with mock.patch("subprocess.run", return_value=fake_process):
                with mock.patch("cherenkov.execution.perf_analyzer.PerformanceAnalyzer") as MockAnalyzer:
                    instance = MockAnalyzer.return_value
                    instance.record_latency.return_value = None
                    instance.analyze_anomaly.return_value = {
                        "status": "ok",
                        "message": "Performance verification completed.",
                    }
                    report = runner.run_k6_validation("http://localhost:8000")
        self.assertEqual(report["status"], "success")
        self.assertIn("http_req_duration", report["metrics"])
        self.assertIn("123.45ms", report["metrics"]["http_req_duration"])


if __name__ == "__main__":
    unittest.main()
