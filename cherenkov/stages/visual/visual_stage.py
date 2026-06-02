"""
CHERENKOV stages/visual/visual_stage.py — Phase B1 Visual Regression stage.
Authority: v3.1 + delta.

Optional capability layer on top of Track A. Never replaces API conformance.
Reuses Track A contracts (VisualSlice/VisualReport/Verdict/GateResult) and the
Track A PlaywrightRunner for execution. Output remains ejectable.

Suggest-only (Delta D7): user-owned test files are NEVER auto-modified.
The runner's own scratchpad spec under stub/generated_tests/ is the runner's
domain — same pattern Track A's validate/healing already use.
Baselines are written ONLY when missing (auto-init) or when init_mode=True is
forced at construction time.
"""
from __future__ import annotations

import os
import sys
import time
from cherenkov.core.contracts import (
    StageMeta,
    StageError,
    Status,
    Verdict,
    VisualSlice,
    VisualGateResult,
    VisualReport,
)
from cherenkov.execution.playwright_invoke import PlaywrightRunner


class VisualStage:
    """Runs Playwright visual regression for ONE VisualSlice and returns a VisualReport.

    Per-unit run() contract — matches IngestStage/PlanStage/GenerateStage shape.
    Reuses PlaywrightRunner verbatim (no direct shell-outs) so artifacts stay ejectable.
    """

    def __init__(self, run_id: str | None = None, init_mode: bool = False):
        self.run_id = run_id
        self.init_mode = init_mode
        self.runner = PlaywrightRunner(run_id=run_id)

    def _spec_for_slice(self, sl: VisualSlice) -> str:
        return (
            "import { test, expect } from '@playwright/test';\n\n"
            f"test('visual::{sl.name}', async ({{ page }}) => {{\n"
            f"  await page.setViewportSize({{ width: {sl.viewport_w}, height: {sl.viewport_h} }});\n"
            f"  await page.goto({sl.url!r});\n"
            f"  await expect(page).toHaveScreenshot('{sl.name}.png');\n"
            "});\n"
        )

    def run(self, sl: VisualSlice, baseline_dir: str | None = None) -> VisualReport:
        """Execute visual regression for ONE slice. Auto-initializes baseline if missing."""
        t0 = time.time()
        scenario_id = f"visual_{sl.name}"
        spec = self._spec_for_slice(sl)

        # Playwright stores snapshots at:
        #   stub/generated_tests/{scenario}.spec.ts-snapshots/{slice}-{platform}.png
        # Missing baseline -> auto-promote to init (--update-snapshots).
        snap_dir = os.path.join(self.runner.tests_dir, f"{scenario_id}.spec.ts-snapshots")
        platform = sys.platform if sys.platform in ("linux", "darwin", "win32") else sys.platform
        baseline_file = os.path.join(snap_dir, f"{sl.name}-{platform}.png")
        needs_init = self.init_mode or not os.path.exists(baseline_file)

        result = self.runner.execute_test(
            scenario_id=scenario_id,
            test_code=spec,
            api_url=sl.url,
            update_snapshots=needs_init,
        )

        passed = bool(result.get("passed"))
        baseline_label = (
            f"{baseline_dir.rstrip('/')}/{sl.name}.png" if baseline_dir else f"{sl.name}.png"
        )
        gate = VisualGateResult(
            gate="pixel_diff",
            passed=passed,
            diff_pixels=0 if passed else -1,
            baseline_path=baseline_label,
            actual_path=result.get("test_file", ""),
        )

        errors: list[StageError] = []
        if not passed:
            errors.append(StageError(
                code="VISUAL_MISMATCH",
                detail=result.get("failure_message", "") or "visual diff failed",
                where=sl.name,
            ))

        return VisualReport(
            scenario_id=scenario_id,
            gates=[gate],
            verdict=Verdict.AUTO_APPROVE if passed else Verdict.HITL,
            status=Status.OK if passed else Status.FAILED,
            errors=errors,
            metadata=StageMeta(stage="visual", duration_ms=int((time.time() - t0) * 1000)),
        )
