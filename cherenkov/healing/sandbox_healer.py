"""
CHERENKOV healing/sandbox_healer.py -- premium isolated deep self-healing sandbox engine.
Authority: v3.1 + delta.

D7 invariant: never auto-edits test code. All heal output is diff-only suggestions.
Anti-lock-in: provider abstraction allows filesystem (default) or Docker sandbox.
"""

from __future__ import annotations

import os
import time
import uuid
import difflib

from cherenkov.core.errors import get_logger
from cherenkov.core.settings import get_settings
from cherenkov.ai.ollama_client import complete_code, strip_think
from cherenkov.healing.providers.base import SandboxProvider
from cherenkov.healing.providers.filesystem import FilesystemSandboxProvider
from cherenkov.healing.providers.docker_sandbox import DockerSandboxProvider

SYSTEM_PROMPT = """You are an expert QA automation engineer specializing in fixing failing Playwright TypeScript E2E API tests.
Your goal is to repair the failing test so that it matches the OpenAPI contract constraints and passes successfully.

CRITICAL INSTRUCTIONS:
- You must ONLY output the corrected TypeScript code. No explanations, no markdown fences, no leading/trailing prose.
- Respect the OpenAPI spec and target server return codes: fix assert status codes or body property shapes to match actual responses described in the error log.
- Do NOT rewrite or lose original HTTP POST payload fields unless specifically necessary to correct a validation error described in the log.
- Fix broken locators or assertions to be syntactically correct.

EXAMPLE OF CORRECT REPAIR OUTPUT:
import { test, expect } from '@playwright/test';

test('corrected test scenario', async ({ page }) => {
  // Corrected locators or assert status
  expect(response.status).toBe(400);
});
"""


class SandboxHealer:
    """Manages isolated workspace replication and runs the run-and-repair LLM self-healing cycle."""

    def __init__(self, run_id: str | None = None, provider: str = "filesystem"):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.log = get_logger("SANDBOX_HEALER", self.run_id)
        self.stub_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../stub")
        )
        self.cherenkov_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../.cherenkov")
        )
        self.provider = self._resolve_provider(provider)

    def _resolve_provider(self, name: str) -> SandboxProvider:
        if name == "docker":
            return DockerSandboxProvider(cherenkov_dir=self.cherenkov_dir)
        return FilesystemSandboxProvider(cherenkov_dir=self.cherenkov_dir)

    def set_provider(self, name: str) -> None:
        self.provider = self._resolve_provider(name)
        self.log.info("sandbox provider switched", provider=name)

    def replicate_workspace(self, scenario_id: str) -> str:
        """Delegates to the active sandbox provider."""
        self.log.info(
            "replicating workspace via provider", provider=type(self.provider).__name__
        )
        return self.provider.replicate_workspace(
            f"{self.run_id}_{scenario_id}", self.stub_dir
        )

    def execute_playwright_sandbox(
        self, sandbox_dir: str, spec_filename: str, api_url: str
    ) -> dict:
        """Delegates to the active sandbox provider."""
        self.log.info(
            "executing playwright test via provider",
            provider=type(self.provider).__name__,
        )
        result = self.provider.execute_test(sandbox_dir, spec_filename, api_url)
        return {
            "passed": result.passed,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def generate_unified_diff(
        self, original_code: str, healed_code: str, filename: str
    ) -> str:
        orig_lines = original_code.splitlines(keepends=True)
        heal_lines = healed_code.splitlines(keepends=True)

        diff = difflib.unified_diff(
            orig_lines,
            heal_lines,
            fromfile=f"a/generated_tests/{filename}",
            tofile=f"b/generated_tests/{filename}",
        )
        return "".join(diff)

    def run_deep_healing(
        self,
        scenario_id: str,
        original_test_filename: str,
        failure_log: str,
        api_url: str,
        max_attempts: int = 3,
    ) -> dict:
        """Runs iterative repair loops in the sandbox and returns a unified diff if repaired."""
        t0 = time.time()
        self.log.info(
            "initiating deep self-healing cycle",
            scenario=scenario_id,
            attempts=max_attempts,
        )

        original_file_path = os.path.join(
            self.stub_dir, "generated_tests", original_test_filename
        )
        if not os.path.exists(original_file_path):
            error_msg = f"Original spec file {original_test_filename} not found."
            self.log.error(error_msg)
            return {"healed": False, "message": error_msg}

        with open(original_file_path, "r", encoding="utf-8") as f:
            original_code = f.read()

        sandbox_dir = self.replicate_workspace(scenario_id)
        spec_workspace_path = f"generated_tests/{original_test_filename}"

        current_code = original_code
        current_failure = failure_log

        for attempt in range(1, max_attempts + 1):
            self.log.info("running repair sweep", attempt=attempt)

            user_prompt = (
                "ORIGINAL FAILING CODE:\n"
                f"```typescript\n{current_code}\n```\n\n"
                "PLAYWRIGHT ERROR LOG / DRIFT DETAILS:\n"
                f"```\n{current_failure}\n```\n\n"
                "CRITICAL GOAL:\n"
                "Analyze the assertion or schema failure, repair it, and output ONLY the complete "
                "TypeScript test file code with appropriate locators or status codes corrected."
            )

            try:
                proposed_raw = complete_code(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    model=get_settings().GEN_MODEL,
                    run_id=self.run_id,
                )
                proposed_code = strip_think(proposed_raw)

                self.provider.write_file(
                    sandbox_dir, spec_workspace_path, proposed_code
                )

                self.log.info("verifying proposed code in sandbox...")
                run_res = self.execute_playwright_sandbox(
                    sandbox_dir, original_test_filename, api_url
                )

                if run_res["passed"]:
                    self.log.info(
                        "self-healing successful! Green state achieved in sandbox",
                        attempt=attempt,
                    )

                    diff_str = self.generate_unified_diff(
                        original_code, proposed_code, original_test_filename
                    )

                    diffs_dir = os.path.join(self.cherenkov_dir, "healed_diffs")
                    os.makedirs(diffs_dir, exist_ok=True)
                    diff_file_path = os.path.join(diffs_dir, f"{scenario_id}.diff")
                    with open(diff_file_path, "w", encoding="utf-8") as df:
                        df.write(diff_str)

                    self.provider.destroy_workspace(sandbox_dir)

                    dt = int((time.time() - t0) * 1000)
                    return {
                        "healed": True,
                        "attempts": attempt,
                        "duration_ms": dt,
                        "diff_path": diff_file_path,
                        "diff": diff_str,
                        "code": proposed_code,
                        "message": f"Test successfully healed in sandbox on attempt {attempt}!",
                    }

                else:
                    self.log.warning(
                        "proposed repair failed to pass in sandbox", attempt=attempt
                    )
                    current_code = proposed_code
                    current_failure = run_res["stderr"] or run_res["stdout"]

            except Exception as e:
                self.log.error(
                    "sandbox repair cycle error", attempt=attempt, error=str(e)
                )
                current_failure = f"Sandbox execution threw exception: {e}"

        self.provider.destroy_workspace(sandbox_dir)
        return {
            "healed": False,
            "attempts": max_attempts,
            "message": f"Deep self-healing completed but failed to achieve a green state in {max_attempts} attempts.",
        }
