"""
CHERENKOV execution/k6_runner.py — local k6 performance script exporter and validation runner.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from cherenkov.core.errors import get_logger
from cherenkov.core.config import Config

class K6Runner:
    """Exports structured local k6 load test scripts and runs them programmatically to capture system metrics."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("K6_RUNNER", run_id)
        self.stub_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../stub"))
        self.tests_dir = os.path.join(self.stub_dir, "generated_tests")
        self.k6_script_path = os.path.join(self.tests_dir, "k6_perf.js")

    def export_k6_script(self, target_url: str) -> str:
        """Generates a standard JavaScript k6 performance script targeting the user creation API."""
        os.makedirs(self.tests_dir, exist_ok=True)

        k6_code = f"""import http from 'k6/http';
import {{ check, sleep }} from 'k6';

export const options = {{
  vus: 5,
  duration: '3s',
  thresholds: {{
    http_req_duration: ['p(95)<500'], // 95% of requests must complete below 500ms
    http_req_failed: ['rate<0.05'],    // Error rate must be less than 5%
  }},
}};

export default function () {{
  const url = `${{__ENV.API_URL || '{target_url}'}}/users`;
  const payload = JSON.stringify({{
    email: `k6_perf_${{Math.random()}}@cherenkov.local`,
    password: 'secure_password_123',
  }});

  const params = {{
    headers: {{
      'Content-Type': 'application/json',
    }},
  }};

  const res = http.post(url, payload, params);
  check(res, {{
    'status is 201': (r) => r.status === 201,
  }});
  sleep(0.1);
}}
"""
        with open(self.k6_script_path, "w", encoding="utf-8") as f:
            f.write(k6_code)

        self.log.info("exported standard k6 performance script", path=self.k6_script_path)
        return k6_code

    def run_k6_validation(self, api_url: str | None = None) -> dict:
        """Runs the exported k6 script natively. If k6 executable is missing, returns graceful export details."""
        url = api_url or Config.API_URL
        self.export_k6_script(url)

        # Check if k6 is installed in the system PATH
        k6_bin = shutil.which("k6")
        if not k6_bin:
            self.log.warning("k6 binary is not installed locally. Skipping performance runner execution.")
            return {
                "status": "exported",
                "message": "Performance test script successfully generated. k6 runner skipped (k6 binary not found in PATH).",
                "script_path": self.k6_script_path,
                "api_url": url,
                "instructions": "Install k6 (https://grafana.com/docs/k6/latest/set-up/install-k6/) and run: k6 run " + self.k6_script_path
            }

        self.log.info("invoking k6 performance runner", bin=k6_bin, script=self.k6_script_path)
        
        env = os.environ.copy()
        env["API_URL"] = url

        process = subprocess.run(
            [k6_bin, "run", self.k6_script_path],
            env=env,
            capture_output=True,
            text=True
        )

        passed = (process.returncode == 0)
        report = {
            "status": "success" if passed else "failed",
            "exit_code": process.returncode,
            "api_url": url,
            "script_path": self.k6_script_path,
            "metrics": {},
            "raw_output": process.stdout
        }

        # Parse metrics from k6 output
        stdout = process.stdout
        metrics = {}
        for line in stdout.splitlines():
            if "http_req_duration" in line:
                metrics["http_req_duration"] = line.strip()
            elif "http_reqs" in line:
                metrics["http_reqs"] = line.strip()
            elif "http_req_failed" in line:
                metrics["http_req_failed"] = line.strip()
                
        report["metrics"] = metrics
        self.log.info("k6 validation completed", status=report["status"])
        return report
