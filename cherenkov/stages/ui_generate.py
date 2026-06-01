"""
CHERENKOV stages/ui_generate.py — UI E2E test generator stage.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import json
import time
from typing import Any

from cherenkov.core.contracts import GenerateOutput, Status, StageMeta, StageError
from cherenkov.core.config import Config
from cherenkov.ai.ollama_client import complete_code, strip_think
from cherenkov.core.errors import get_logger
from cherenkov.stages.ui_plan import UIScenario, UISpec

SYSTEM_PROMPT = """You are an expert QA automation engineer writing Playwright UI/E2E tests in TypeScript. You write ONE test per request.

STRICT RULES:
- Always import 'test' and 'expect' from '@playwright/test'.
- Use standard Playwright locator actions: page.goto(), page.locator(), locator.fill(), locator.click().
- Every test MUST assert specific UI visual states or feedback elements (e.g. expect(page.locator('#feedback-message')).toContainText('Success') or toBeVisible()).
- Visual tests should use standard Playwright visual comparison: expect(page).toHaveScreenshot('visual-baseline.png').
- Do NOT use third-party libraries; stick to pure standard Playwright E2E actions.
- Output ONLY the test code. No prose, no markdown fences, no explanation.

EXAMPLE OF CORRECT USAGE:
import { test, expect } from '@playwright/test';

test('create user happy path via ui', async ({ page }) => {
  await page.goto('http://localhost:8000/');
  await page.locator('#email-input').fill('test@example.com');
  await page.locator('#password-input').fill('password123');
  await page.locator('#submit-button').click();
  await expect(page.locator('#feedback-message')).toContainText('Success');
});
"""

class UIGenerateStage:
    """Invokes local LLM qwen2.5-coder to write standard Playwright TypeScript UI/E2E tests."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("UI_GENERATE", run_id)

    def _build_user_prompt(
        self,
        ui_spec: UISpec,
        scenario: UIScenario
    ) -> str:
        """Constructs E2E UI generation prompt payload."""
        return (
            "TARGET UI URL:\n"
            + f"  {ui_spec.url}\n\n"
            + "DISCOVERED INTERACTIVE ELEMENTS:\n"
            + json.dumps([e.model_dump() for e in ui_spec.elements], indent=2)
            + "\n\nSCENARIO:\n"
            + f"  id: {scenario.id}\n"
            + f"  name: {scenario.name}\n"
            + f"  description: {scenario.description}\n"
            + f"  steps to automate:\n"
            + json.dumps(scenario.steps, indent=2)
            + "\n=== CRITICAL INSTRUCTIONS AND EXAMPLE ===\n"
            + "Write the Playwright UI/E2E test in TypeScript adhering to standard Playwright rules now."
        )

    def run(
        self,
        ui_spec: UISpec,
        scenario: UIScenario
    ) -> GenerateOutput:
        t0 = time.time()
        self.log.info("stage start", scenario_id=scenario.id)

        user_prompt = self._build_user_prompt(ui_spec, scenario)

        try:
            # 1. Complete raw code generation via local model
            raw_code = complete_code(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model=Config.GEN_MODEL,
                run_id=self.run_id
            )
            
            # 2. Brutal DeepSeek <think> strip (if any)
            code = strip_think(raw_code)
            
            # Auto-heal missing expect import if expect assertion is used in generated code
            if "expect(" in code:
                lines = code.splitlines()
                for i, line in enumerate(lines):
                    if "@playwright/test" in line and "expect" not in line:
                        if "{ test }" in line:
                            lines[i] = line.replace("{ test }", "{ test, expect }")
                        elif "test" in line and "{" in line and "}" in line:
                            # Handle other brace spacing variations, e.g. {test} or {  test  }
                            lines[i] = line.replace("test", "test, expect")
                        else:
                            # Fallback if somehow braces are not matching standard shape
                            lines[i] = "import { test, expect } from '@playwright/test';"
                code = "\n".join(lines)


            
        except Exception as e:
            error_msg = f"Ollama generation failed for E2E UI test: {e}"
            self.log.error(error_msg)
            return GenerateOutput(
                scenario_id=scenario.id,
                test_code="",
                status=Status.FAILED,
                errors=[StageError(code="OLLAMA_GENERATION_FAILED", detail=error_msg)],
                metadata=StageMeta(stage="UI_GENERATE", duration_ms=0)
            )

        dt = int((time.time() - t0) * 1000)
        self.log.info("stage success", duration_ms=dt)

        return GenerateOutput(
            scenario_id=scenario.id,
            test_code=code,
            imports=["@playwright/test"],
            status=Status.OK,
            metadata=StageMeta(stage="UI_GENERATE", duration_ms=dt)
        )

