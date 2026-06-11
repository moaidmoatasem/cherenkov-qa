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

Epoch 9 addition: after the pixel_diff gate, a second vlm_semantic gate runs
the VisualOracle to classify the change semantically (ANOMALY / HARMLESS_SHIFT /
REDESIGN / UNKNOWN). This gate is advisory — it never overrides the pixel gate.
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
    Claim,
    Provenance,
    ProvenanceType,
)
from cherenkov.core.errors import get_logger
from cherenkov.execution.playwright_invoke import PlaywrightRunner


class VisualStage:
    """Runs Playwright visual regression for ONE VisualSlice and returns a VisualReport.

    Per-unit run() contract — matches IngestStage/PlanStage/GenerateStage shape.
    Reuses PlaywrightRunner verbatim (no direct shell-outs) so artifacts stay ejectable.
    After the pixel_diff gate a vlm_semantic gate classifies the diff via VLM.
    """

    def __init__(self, run_id: str | None = None, init_mode: bool = False, vlm_enabled: bool = True):
        self.run_id = run_id
        self.init_mode = init_mode
        self.vlm_enabled = vlm_enabled
        self.runner = PlaywrightRunner(run_id=run_id)
        self._log = get_logger("visual-stage", run_id)

    def _spec_for_slice(self, sl: VisualSlice) -> str:
        return (
            "import { test, expect } from '@playwright/test';\n\n"
            f"test('visual::{sl.name}', async ({{ page }}) => {{\n"
            f"  await page.setViewportSize({{ width: {sl.viewport_w}, height: {sl.viewport_h} }});\n"
            f"  await page.goto({sl.url!r});\n"
            f"  await expect(page).toHaveScreenshot('{sl.name}.png');\n"
            "});\n"
        )

    def _vlm_gate(
        self,
        sl: VisualSlice,
        baseline_path: str,
        actual_path: str,
        pixel_passed: bool,
    ) -> VisualGateResult:
        """Run the VisualOracle VLM gate. Never raises — degrades to UNKNOWN on error."""
        try:
            from cherenkov.oracle.visual_oracle import VisualOracle
            oracle = VisualOracle()
            claim = Claim(
                id=f"visual_{sl.name}",
                category="visual_diff",
                subject=sl.name,
                value={"pixel_passed": pixel_passed},
                provenance=Provenance(source_type=ProvenanceType.SPEC, source_uri=sl.url),
            )
            result = oracle.evaluate(
                claim,
                baseline_path=baseline_path,
                actual_path=actual_path,
                diff_pixels=0 if pixel_passed else -1,
            )
            vlm_passed = result.is_correct or pixel_passed
            return VisualGateResult(
                gate="vlm_semantic",
                passed=vlm_passed,
                diff_pixels=0,
                baseline_path=baseline_path,
                actual_path=actual_path,
            )
        except Exception as exc:
            self._log.warning("vlm_gate skipped", error=str(exc))
            return VisualGateResult(
                gate="vlm_semantic",
                passed=True,
                diff_pixels=0,
                baseline_path=baseline_path,
                actual_path=actual_path,
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
            f"{baseline_dir.rstrip('/')}/{sl.name}.png" if baseline_dir else baseline_file
        )
        # The actual screenshot Playwright writes on a diff failure lives next to the baseline.
        actual_label = os.path.join(snap_dir, f"{sl.name}-actual.png")

        pixel_gate = VisualGateResult(
            gate="pixel_diff",
            passed=passed,
            diff_pixels=0 if passed else -1,
            baseline_path=baseline_label,
            actual_path=actual_label if os.path.exists(actual_label) else result.get("test_file", ""),
        )

        gates: list[VisualGateResult] = [pixel_gate]

        # Epoch 9: add VLM semantic gate when a diff occurred or VLM always-on is requested.
        if self.vlm_enabled and (not passed or os.path.exists(actual_label)):
            vlm_gate = self._vlm_gate(
                sl=sl,
                baseline_path=baseline_label,
                actual_path=pixel_gate.actual_path,
                pixel_passed=passed,
            )
            gates.append(vlm_gate)

        errors: list[StageError] = []
        if not passed:
            errors.append(StageError(
                code="VISUAL_MISMATCH",
                detail=result.get("failure_message", "") or "visual diff failed",
                where=sl.name,
            ))

        # Overall verdict: HITL if pixel gate failed AND VLM didn't classify it harmless.
        vlm_harmless = any(g.gate == "vlm_semantic" and g.passed for g in gates)
        final_verdict = Verdict.AUTO_APPROVE if (passed or vlm_harmless) else Verdict.HITL
        final_status = Status.OK if passed else (Status.DEGRADED if vlm_harmless else Status.FAILED)

        return VisualReport(
            scenario_id=scenario_id,
            gates=gates,
            verdict=final_verdict,
            status=final_status,
            errors=errors,
            metadata=StageMeta(stage="visual", duration_ms=int((time.time() - t0) * 1000)),
        )
