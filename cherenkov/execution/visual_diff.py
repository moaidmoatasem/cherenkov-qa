"""
CHERENKOV execution/visual_diff.py — Visual snapshot baseline and comparison engine.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os
import subprocess
from cherenkov.core.errors import get_logger
from cherenkov.core.config import Config

class VisualDiffEngine:
    """Manages verified visual screenshot baseline snapshots and executes structural diffing checks."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("VISUAL_DIFF", run_id)
        self.stub_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../stub"))
        self.snapshots_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.cherenkov/snapshots"))

    def run_visual_validation(self, api_url: str | None = None) -> dict:
        """Executes the visual E2E test. If baseline snapshots are absent, initializes them via --update-snapshots."""
        url = api_url or Config.API_URL
        self.log.info("starting visual regression checks", target_url=url)

        # Ensure snapshots directory exists or check if snapshots are present
        snapshots_exist = os.path.exists(self.snapshots_dir) and any(
            f.endswith(".png") for f in os.listdir(self.snapshots_dir)
        ) if os.path.exists(self.snapshots_dir) else False

        if not snapshots_exist:
            self.log.info("visual baseline snapshot not found, initializing baseline using --update-snapshots")
            # Enforce snapshot generation via Playwright --update-snapshots
            npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
            cmd = [
                npx_cmd, "playwright", "test",
                "generated_tests/visual_regression_baseline_ui.spec.ts",
                "--update-snapshots"
            ]
            env = os.environ.copy()
            env["API_URL"] = url
            
            subprocess.run(
                cmd,
                cwd=self.stub_dir,
                env=env,
                capture_output=True,
                text=True
            )
            self.log.info("visual baseline snapshot successfully initialized", path=self.snapshots_dir)

        # Run validation
        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
        cmd = [
            npx_cmd, "playwright", "test",
            "generated_tests/visual_regression_baseline_ui.spec.ts",
            "--reporter=json"
        ]
        env = os.environ.copy()
        env["API_URL"] = url

        process = subprocess.run(
            cmd,
            cwd=self.stub_dir,
            env=env,
            capture_output=True,
            text=True
        )

        passed = (process.returncode == 0)
        report = {
            "passed": passed,
            "exit_code": process.returncode,
            "target_url": url,
            "baseline_dir": self.snapshots_dir,
            "mismatch_detected": not passed
        }

        if passed:
            self.log.info("visual verification passed - layout matches baseline snapshot")
            if not snapshots_exist:
                report["message"] = "Visual baseline initialized successfully. No prior snapshot to compare against."
            else:
                report["message"] = "Visual verification passed successfully. No UI layout deviations detected."
        else:
            self.log.warning("visual mismatch detected - UI layout deviates from baseline snapshot")
            report["message"] = "Visual verification failed. Mismatch detected between live UI and baseline snapshot."
            report["error_output"] = process.stderr or process.stdout

        return report
