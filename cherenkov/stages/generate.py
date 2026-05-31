"""
CHERENKOV stages/generate.py — real recency-anchored test generator stage.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import json
import time
from typing import Any

from cherenkov.core.contracts import GenerateOutput, Scenario, Status, StageMeta, StageError
from cherenkov.core.config import Config
from cherenkov.ai.ollama_client import complete_code, strip_think
from cherenkov.core.errors import get_logger

SYSTEM_PROMPT = """You are an expert QA automation engineer writing Playwright API tests in TypeScript. You write ONE test per request.

STRICT RULES:
- Use ONLY the provided openapi-fetch client (client.GET/POST/PUT/DELETE). NEVER use fetch, axios, or Playwright's raw request context directly.
- Always import the client using: import { client } from '../client';
- Always import 'test' and 'expect' from '@playwright/test'.
- Every test MUST assert the SPECIFIC expected HTTP status code (e.g. expect(response.status).toBe(201)) — never a range like toBeLessThan(500).
- Every test MUST assert the response body SHAPE: the specific named properties that should exist and their types (e.g. expect(data).toHaveProperty('id')).
- Do NOT assert specific string values (the mock returns placeholder values).
- Use the test runner's assertion mechanisms (expect(...)). Do NOT throw custom errors (e.g. if (!res.ok) throw new Error()). The runner must see the assertion to report pass/fail correctly.
- Output ONLY the test code. No prose, no markdown fences, no explanation.

EXAMPLE OF CORRECT USAGE:
import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create user happy path', async () => {
  const { data, response } = await client.POST('/users', {
    body: { email: 'test@example.com', password: 'password123' }
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
});

test('get health happy path', async () => {
  const { data, response } = await client.GET('/health');
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('status');
});
"""

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
            + f"  instruction: {instruction}\n"
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
            
        except Exception as e:
            error_msg = f"Ollama generation failed: {e}"
            self.log.error(error_msg)
            return GenerateOutput(
                scenario_id=scenario.mutation_id or "unknown",
                test_code="",
                status=Status.FAILED,
                errors=[StageError(code="OLLAMA_GENERATION_FAILED", detail=error_msg)],
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
