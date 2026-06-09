"""
CHERENKOV stages/generate.py — real recency-anchored test generator stage.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

from cherenkov.core.contracts import GenerateOutput, Scenario, Status, StageMeta, StageError
from cherenkov.core.config import Config
from cherenkov.core.compat import npx as _npx
from cherenkov.ai import get_client
from cherenkov.ai.ollama_client import strip_think
from cherenkov.core.errors import get_logger


def _sanitize_prompt_input(text: str, max_len: int = 500) -> str:
    """Strip prompt injection markers and limit length."""
    injection_markers = ["\n\nSystem:", "\n\nHuman:", "\n\nAssistant:", "###", "---\nINSTRUCT", "<|im_start|>", "<|system|>"]
    sanitized = text
    for marker in injection_markers:
        if marker in sanitized:
            sanitized = sanitized[:sanitized.index(marker)]
    # Keep printable ASCII only, enforce max length
    sanitized = sanitized.encode("ascii", errors="ignore").decode()[:max_len]
    return sanitized.strip()


def _load_system_prompt() -> str:
    """Loads the tuned generator system prompt committed to prompts/generator_system.txt.

    Read once at import so it remains a static constant (prefix-cache optimization on
    Ollama, per Delta D10 / V1). Resolved relative to the repo root, with the
    CHERENKOV_GENERATOR_PROMPT env var as an override.
    """
    override = os.getenv("CHERENKOV_GENERATOR_PROMPT")
    prompt_path = override or os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../prompts/generator_system.txt")
    )
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


# Tuned generator prompt committed to prompts/generator_system.txt (loaded once at import).
SYSTEM_PROMPT = _load_system_prompt()

class GenerateStage:
    """Invokes local LLM qwen2.5-coder to write compile-ready Playwright TypeScript tests."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("GENERATE", run_id)

    def _build_user_prompt(
        self,
        path: str,
        method: str,
        operation: dict[str, Any],
        schemas: dict[str, Any],
        scenario: Scenario,
        instruction: str
    ) -> str:
        """Constructs a recency-anchored prompt payload, placing strict openapi-fetch rules at the absolute end to override model semantic bias."""
        return (
            "ENDPOINT SLICE (the only schema you need):\n"
            + json.dumps(
                {
                    "path": path,
                    "method": method,
                    "operation": operation,
                    "schemas": schemas,
                },
                indent=2,
            )
            + "\n\nSCENARIO:\n"
            + f"  endpoint: {method} {path}\n"
            + f"  case_type: {scenario.case_type}\n"
            + f"  mutation_id: {scenario.mutation_id}\n"
            + f"  instruction: {_sanitize_prompt_input(instruction)}\n"
            + f"  expected_status: {scenario.expected_status}\n"
            + "\n=== CRITICAL INSTRUCTIONS AND EXAMPLE ===\n"
            + "You are writing a Playwright API test in TypeScript using openapi-fetch client.\n"
            + "STRICT RULES:\n"
            + "- Import the client exactly as: import { client } from '../client';\n"
            + "- Import 'test' and 'expect' from '@playwright/test'.\n"
            + "- Use ONLY the provided openapi-fetch client (e.g. const { data, response } = await client.POST('/path', { body: {...} })).\n"
            + "- Do NOT use standard Playwright 'request' directly. Do NOT use default imports for 'client'.\n"
            + "- Every test MUST assert the specific HTTP status code: expect(response.status).toBe(expected_status) (status is a PROPERTY, not a function!).\n"
            + "- Every test MUST assert the response body shape: expect(data).toHaveProperty('property_name') (body shape is in the destructured 'data' object!).\n"
            + "- Output ONLY the TypeScript code block starting with the imports. No prose, no explanations, no markdown fences.\n"
            + "\nEXAMPLE OF CORRECT USAGE:\n"
            + "import { client } from '../client';\n"
            + "import { test, expect } from '@playwright/test';\n\n"
            + "test('get health happy path', async () => {\n"
            + "  const { data, response } = await client.GET('/health');\n"
            + "  expect(response.status).toBe(200);\n"
            + "  expect(data).toHaveProperty('status');\n"
            + "});\n\n"
            + "test('create user happy path', async () => {\n"
            + "  const { data, response } = await client.POST('/users', {\n"
            + "    body: { email: 'test@example.com', password: 'password123' }\n"
            + "  });\n"
            + "  expect(response.status).toBe(201);\n"
            + "  expect(data).toHaveProperty('id');\n"
            + "});\n\n"
            + "Write the Playwright API test adhering to these critical rules now."
        )

    def run(
        self,
        scenario: Scenario,
        path: str,
        method: str,
        operation: dict[str, Any],
        schemas: dict[str, Any],
        instruction: str
    ) -> GenerateOutput:
        t0 = time.time()
        self.log.info("stage start", scenario_id=scenario.mutation_id)

        user_prompt = self._build_user_prompt(
            path=path,
            method=method,
            operation=operation,
            schemas=schemas,
            scenario=scenario,
            instruction=instruction
        )

        # temperatures: start with variation, tighten on repair attempts
        temperatures = [0.2, 0.1, 0.05]
        code = ""
        last_error = ""

        # Make temp directory for tsc check
        stub_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../stub"))
        temp_dir = os.path.join(stub_dir, "generated_tests")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, f"temp_{scenario.mutation_id}.spec.ts")

        for temp in temperatures:
            try:
                # 1. Complete raw code generation via configured provider
                client = get_client()
                raw_code = client.complete_code(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    model=Config.GEN_MODEL,
                    temperature=temp,
                    run_id=self.run_id
                )
                
                # 2. Brutal DeepSeek <think> strip (if any)
                code = strip_think(raw_code)

                # 3. Write temp file and check tsc --noEmit
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(code)
                
                import subprocess
                process = subprocess.run(
                    [_npx(), "tsc", "--noEmit"],
                    cwd=stub_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if process.returncode == 0:
                    break
                else:
                    last_error = f"TSC failed: {process.stderr[:100]}"
                    self.log.warning("tsc compilation failed, retrying with higher temperature", temperature=temp, error=last_error)
            except Exception as e:
                last_error = f"Ollama generation failed: {e}"
                self.log.warning("generation exception, retrying with higher temperature", temperature=temp, error=last_error)

        if os.path.exists(temp_file):
            os.remove(temp_file)

        if not code or (last_error and "TSC failed" not in last_error and "Ollama" in last_error):
            self.log.error(last_error)
            return GenerateOutput(
                scenario_id=scenario.mutation_id or "unknown",
                test_code="",
                status=Status.FAILED,
                errors=[StageError(code="OLLAMA_GENERATION_FAILED", detail=last_error)],
                metadata=StageMeta(stage="GENERATE", duration_ms=0)
            )

        dt = int((time.time() - t0) * 1000)
        self.log.info("stage success", duration_ms=dt)

        return GenerateOutput(
            scenario_id=scenario.mutation_id or "unknown",
            test_code=code,
            imports=["@playwright/test", "../client"],
            status=Status.OK,
            metadata=StageMeta(stage="GENERATE", duration_ms=dt)
        )
