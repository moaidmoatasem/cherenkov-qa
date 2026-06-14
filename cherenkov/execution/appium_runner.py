from __future__ import annotations
import subprocess
from pathlib import Path
import requests

from cherenkov.execution.mobile_runner_base import MobileRunnerBase


class AppiumRunner(MobileRunnerBase):
    def __init__(self, appium_server: str = "http://localhost:4723", timeout: int = 30):
        self.appium_server = appium_server
        self.timeout = timeout

    def run_test(self, test_path: str) -> dict:
        if self.dry_run:
            return self._dry_run_result(test_path)

        path = Path(test_path)
        if not path.exists():
            return {"status": "failed", "error": f"Test file not found: {test_path}"}

        result = subprocess.run(
            ["pytest", str(path), f"--appium-server={self.appium_server}"],
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

        return {
            "status": "passed" if result.returncode == 0 else "failed",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def health_check(self) -> bool:
        if self.dry_run:
            return True
        try:
            resp = requests.get(f"{self.appium_server}/status", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
