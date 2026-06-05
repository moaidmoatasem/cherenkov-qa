"""
CHERENKOV healing/sandbox_healer.py -- premium isolated deep self-healing sandbox engine.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
import uuid
import difflib
from cherenkov.core.errors import get_logger
from cherenkov.core.config import Config
from cherenkov.core.compat import npx as _npx
from cherenkov.ai.ollama_client import complete_code, strip_think

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

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.log = get_logger("SANDBOX_HEALER", self.run_id)
        self.stub_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../stub"))
        self.cherenkov_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.cherenkov"))

    def replicate_workspace(self, scenario_id: str) -> str:
        """Replicates E2E stubs to an isolated sandbox, utilizing symlinks for node_modules for extreme speed."""
        sandbox_path = os.path.join(self.cherenkov_dir, f"sandbox_{self.run_id}_{scenario_id}")
        self.log.info("replicating stub workspace to sandbox", path=sandbox_path)

        if os.path.exists(sandbox_path):
            shutil.rmtree(sandbox_path)
        os.makedirs(sandbox_path, exist_ok=True)

        # Copy stub configuration and type files (exclude node_modules, generated_tests, test-results)
        ignore_patterns = shutil.ignore_patterns("node_modules", "generated_tests", "test-results")
        for item in os.listdir(self.stub_dir):
            s = os.path.join(self.stub_dir, item)
            d = os.path.join(sandbox_path, item)
            if os.path.isdir(s):
                if item not in ("node_modules", "generated_tests", "test-results"):
                    shutil.copytree(s, d, symlinks=True)
            else:
                shutil.copy2(s, d)

        # Create generated_tests directory inside the sandbox
        os.makedirs(os.path.join(sandbox_path, "generated_tests"), exist_ok=True)

        # Symlink node_modules to avoid copying gigabytes of dependencies
        parent_node_modules = os.path.join(self.stub_dir, "node_modules")
        sandbox_node_modules = os.path.join(sandbox_path, "node_modules")
        if os.path.exists(parent_node_modules):
            try:
                os.symlink(parent_node_modules, sandbox_node_modules)
                self.log.info("successfully symlinked node_modules to sandbox")
            except Exception as e:
                self.log.warning("failed to symlink node_modules, attempting copy", error=str(e))
                # Fallback to absolute copy if symlinking is blocked by platform settings
                shutil.copytree(parent_node_modules, sandbox_node_modules, symlinks=True)

        return sandbox_path

    def execute_playwright_sandbox(self, sandbox_dir: str, spec_filename: str, api_url: str) -> dict:
        """Natively runs the specific spec test in the sandbox environment."""
        spec_path = f"generated_tests/{spec_filename}"
        self.log.info("executing playwright test in sandbox", spec=spec_path)

        env = os.environ.copy()
        env["API_URL"] = api_url

        process = subprocess.run(
            [_npx(), "playwright", "test", spec_path, "--reporter=json"],
            cwd=sandbox_dir,
            env=env,
            capture_output=True,
            text=True
        )

        passed = (process.returncode == 0)
        return {
            "passed": passed,
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr
        }

    def generate_unified_diff(self, original_code: str, healed_code: str, filename: str) -> str:
        """Generates standard git-diff format from original code to corrected code."""
        orig_lines = original_code.splitlines(keepends=True)
        heal_lines = healed_code.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            orig_lines,
            heal_lines,
            fromfile=f"a/generated_tests/{filename}",
            tofile=f"b/generated_tests/{filename}"
        )
        return "".join(diff)

    def run_deep_healing(
        self,
        scenario_id: str,
        original_test_filename: str,
        failure_log: str,
        api_url: str,
        max_attempts: int = 3
    ) -> dict:
        """Runs iterative repair loops in the sandbox and returns a unified diff if repaired."""
        t0 = time.time()
        self.log.info("initiating deep self-healing cycle", scenario=scenario_id, attempts=max_attempts)

        original_file_path = os.path.join(self.stub_dir, "generated_tests", original_test_filename)
        if not os.path.exists(original_file_path):
            error_msg = f"Original spec file {original_test_filename} not found."
            self.log.error(error_msg)
            return {"healed": False, "message": error_msg}

        with open(original_file_path, "r", encoding="utf-8") as f:
            original_code = f.read()

        # Step 1: Replicate isolated workspace
        sandbox_dir = self.replicate_workspace(scenario_id)
        sandbox_file_path = os.path.join(sandbox_dir, "generated_tests", original_test_filename)

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
                # 1. Ask Qwen Coder to repair the failing test
                proposed_raw = complete_code(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    model=Config.GEN_MODEL,
                    run_id=self.run_id
                )
                proposed_code = strip_think(proposed_raw)

                # 2. Write corrected code into the sandbox spec file
                with open(sandbox_file_path, "w", encoding="utf-8") as sf:
                    sf.write(proposed_code)

                # 3. Test corrected code in sandbox
                self.log.info("verifying proposed code in sandbox...")
                run_res = self.execute_playwright_sandbox(sandbox_dir, original_test_filename, api_url)

                if run_res["passed"]:
                    self.log.info("self-healing successful! Green state achieved in sandbox", attempt=attempt)
                    
                    # 4. Generate Unified Diff
                    diff_str = self.generate_unified_diff(original_code, proposed_code, original_test_filename)
                    
                    # Save diff suggestion to local cherenkov store
                    diffs_dir = os.path.join(self.cherenkov_dir, "healed_diffs")
                    os.makedirs(diffs_dir, exist_ok=True)
                    diff_file_path = os.path.join(diffs_dir, f"{scenario_id}.diff")
                    with open(diff_file_path, "w", encoding="utf-8") as df:
                        df.write(diff_str)

                    # Clean up sandbox directory
                    shutil.rmtree(sandbox_dir, ignore_errors=True)

                    dt = int((time.time() - t0) * 1000)
                    return {
                        "healed": True,
                        "attempts": attempt,
                        "duration_ms": dt,
                        "diff_path": diff_file_path,
                        "diff": diff_str,
                        "code": proposed_code,
                        "message": f"Test successfully healed in sandbox on attempt {attempt}!"
                    }

                else:
                    self.log.warning("proposed repair failed to pass in sandbox", attempt=attempt)
                    current_code = proposed_code
                    current_failure = run_res["stderr"] or run_res["stdout"]

            except Exception as e:
                self.log.error("sandbox repair cycle error", attempt=attempt, error=str(e))
                current_failure = f"Sandbox execution threw exception: {e}"

        # If we got here, all attempts failed
        shutil.rmtree(sandbox_dir, ignore_errors=True)
        return {
            "healed": False,
            "attempts": max_attempts,
            "message": f"Deep self-healing completed but failed to achieve a green state in {max_attempts} attempts."
        }
