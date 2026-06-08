"""
CHERENKOV stages/mobile_review.py — Maestro YAML review and validation stage.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from cherenkov.stages.mobile_generate import MobileGenerateOutput


@dataclass
class MobileReviewOutput:
    scenario_id: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    status: str = "ok"


class MobileReviewStage:
    """Validates generated Maestro YAML structure and syntax."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id

    def run(self, generate_output: MobileGenerateOutput) -> MobileReviewOutput:
        t0 = time.time()
        errors: list[str] = []
        yaml_text = generate_output.yaml_content

        if not yaml_text.strip():
            errors.append("Generated YAML is empty")

        if "appId:" not in yaml_text:
            errors.append("Missing required 'appId' field")

        if not re.search(r"^- (tapOn|inputText|assertVisible|assertNotVisible|waitFor|takeScreenshot|runFlow|scrollUntilVisible)", yaml_text, re.MULTILINE):
            errors.append("No Maestro commands found in generated YAML")

        has_indented_value = bool(re.search(r"^\s+text:|^\s+path:|^\s+when:", yaml_text, re.MULTILINE))
        if not has_indented_value:
            errors.append("Commands missing required indented values (text/path/when)")

        passed = len(errors) == 0

        dt = int((time.time() - t0) * 1000)
        if self.run_id:
            print(f"[MOBILE_REVIEW] stage {'passed' if passed else 'failed'} — {len(errors)} errors — {dt}ms")

        return MobileReviewOutput(
            scenario_id=generate_output.scenario_id,
            passed=passed,
            errors=errors,
        )
