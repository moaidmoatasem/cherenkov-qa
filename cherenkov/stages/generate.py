"""
CHERENKOV stages/generate.py — real recency-anchored test generator stage.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

from cherenkov.core.contracts import (
    GenerateOutput,
    Scenario,
    Status,
    StageMeta,
    StageError,
)
from cherenkov.core.settings import get_settings
from cherenkov.ai import get_client
from cherenkov.ai.ollama_client import strip_think
from cherenkov.core.errors import get_logger


def _sanitize_prompt_input(text: str, max_len: int = 500) -> str:
    """Strip prompt injection markers and limit length."""
    injection_markers = [
        "\n\nSystem:",
        "\n\nHuman:",
        "\n\nAssistant:",
        "###",
        "---\nINSTRUCT",
        "<|im_start|>",
        "<|system|>",
    ]
    sanitized = text
    for marker in injection_markers:
        if marker in sanitized:
            sanitized = sanitized[: sanitized.index(marker)]
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
        instruction: str,
        spec_rules_block: str = "",
        strategies_block: str = "",
    ) -> str:
        """Constructs a recency-anchored prompt payload, placing strict openapi-fetch rules at the absolute end to override model semantic bias."""
        enrichment = f"\n\n{spec_rules_block}" if spec_rules_block else ""
        strategies = f"\n\nKnown patterns from past runs:\n{strategies_block}" if strategies_block else ""
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
            + enrichment
            + strategies
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
            + "- Use ONLY the provided openapi-fetch client (e.g. const { data, error, response } = await client.POST('/path', { body: {...} })).\n"
            + "- Do NOT use standard Playwright 'request' directly. Do NOT use default imports for 'client'.\n"
            + "- Every test MUST assert the specific HTTP status code: expect(response.status).toBe(expected_status) (status is a PROPERTY, not a function!).\n"
            + "- IMPORTANT: openapi-fetch puts 2xx response bodies in 'data' and 4xx/5xx response bodies in 'error'. For success tests assert 'data'; for error/validation tests assert 'error'.\n"
            + "- For 4xx tests: const { error, response } = await client.POST(...); expect(response.status).toBe(422); expect(error).toBeTruthy(); expect((error as any).detail).toBeTruthy();\n"
            + "- For 2xx tests: const { data, response } = await client.POST(...); expect(response.status).toBe(201); expect(data).toHaveProperty('id');\n"
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
            + "test('create user missing_email - returns 422', async () => {\n"
            + "  const { error, response } = await client.POST('/users', {\n"
            + "    body: { password: 'password123' } as any\n"
            + "  });\n"
            + "  expect(response.status).toBe(422);\n"
            + "  expect(error).toBeTruthy();\n"
            + "  expect((error as any).detail).toBeTruthy();\n"
            + "});\n\n"
            + "Write the Playwright API test adhering to these critical rules now."
        )

    def run(
        self,
        scenario: Scenario,
        path: str = "",
        method: str = "",
        operation: Optional[dict[str, Any]] = None,
        schemas: Optional[dict[str, Any]] = None,
        instruction: str = "",
        source_type: str = "openapi",
        strategies_block: str = "",
    ) -> GenerateOutput:
        t0 = time.time()
        mutation_id = getattr(
            scenario, "mutation_id", getattr(scenario, "operation_name", "unknown")
        )
        self.log.info("stage start", scenario_id=mutation_id)

        if source_type == "graphql":
            import jinja2

            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(
                    os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "../../prompts")
                    )
                )
            )
            template = env.get_template("graphql_test.j2")
            user_prompt = template.render(
                operation_name=scenario.operation_name,
                kind=scenario.kind,
                gql_query=scenario.gql_query,
                variables=scenario.variables,
                expected_response_structure=scenario.expected_response_structure,
            )
        elif source_type == "grpc":
            import jinja2
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../prompts"))))
            template = env.get_template("grpc_test.j2")
            user_prompt = template.render(
                service=scenario.service,
                rpc_name=scenario.rpc_name,
                input_message=scenario.input_message,
                proto_content=scenario.proto_content
            )
        elif source_type == "accessibility":
            import jinja2

            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(
                    os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "../../prompts")
                    )
                )
            )
            template = env.get_template("accessibility_test.j2")
            user_prompt = template.render(
                scenario_id=scenario.scenario_id,
                page_target=scenario.page_target,
                rules=scenario.rules,
            )
            # Short-circuit LLM since we just use the template for accessibility tests
            code = user_prompt
            dt = int((time.time() - t0) * 1000)
            self.log.info("stage success (template)", duration_ms=dt)
            return GenerateOutput(
                scenario_id=mutation_id,
                test_code=code,
                imports=["@playwright/test", "@axe-core/playwright"],
                status=Status.OK,
                metadata=StageMeta(stage="GENERATE", duration_ms=dt),
            )
        # RESTGPT-style spec enrichment: extract rules + example values from
        # OpenAPI descriptions before building the prompt so the LLM has
        # concrete values to use rather than inventing them.
            spec_rules_block = ""
            try:
                from cherenkov.stages.enrich import SpecEnrichStage

                rules = SpecEnrichStage(run_id=self.run_id).enrich(
                    path=path,
                    method=method,
                    operation=operation or {},
                    schemas=schemas or {},
                )
                if not rules.is_empty():
                    spec_rules_block = rules.render_prompt_block()
            except Exception as enrich_err:
                self.log.warning(
                    "spec enrichment failed (non-fatal)", error=str(enrich_err)
                )

            user_prompt = self._build_user_prompt(
                path=path,
                method=method,
                operation=operation,
                schemas=schemas,
                scenario=scenario,
                instruction=instruction,
                spec_rules_block=spec_rules_block,
                strategies_block=strategies_block,
            )

        from cherenkov.cache.endpoint_cache import EndpointCache

        cache = EndpointCache()
        cache_hash = None

        # Only cache openapi source generations — key includes mutation_id so each
        # scenario gets its own entry rather than sharing one per endpoint.
        if source_type == "openapi":
            cache_hash = cache.compute_hash(
                path,
                method,
                {"op": operation, "sch": schemas, "mid": mutation_id},
                get_settings().GEN_MODEL,
            )
            entry = cache.get(cache_hash)
            if entry:
                self.log.info("cache hit", hash=cache_hash)
                dt = int((time.time() - t0) * 1000)
                return GenerateOutput(
                    scenario_id=mutation_id,
                    test_code=entry.test_code,
                    imports=["@playwright/test", "../client"],
                    status=Status.OK,
                    metadata=StageMeta(stage="GENERATE", duration_ms=dt),
                    endpoint=path,
                    method=method.upper() if method else None,
                )

        # temperatures: start with variation, tighten on repair attempts
        temperatures = [0.2, 0.1, 0.05]
        code = ""
        last_error = ""

        for temp in temperatures:
            try:
                client = get_client()
                raw_code = client.complete_code(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    model=get_settings().GEN_MODEL,
                    temperature=temp,
                    run_id=self.run_id,
                )
                code = strip_think(raw_code)
                if code.strip():
                    break  # TypeScript compilation is validated by Gate 5 in ReviewStage
            except Exception as e:
                last_error = f"Ollama generation failed: {e}"
                self.log.warning(
                    "generation exception, retrying", temperature=temp, error=last_error
                )

        # If Ollama is unavailable or all temperatures failed, fall back to the deterministic
        # template generator so the pipeline continues to completion without a GPU.
        ollama_failed = not code
        if ollama_failed:
            self.log.warning(
                "ollama unavailable — using template generator fallback",
                error=last_error,
            )
            try:
                from cherenkov.ai.template_generator import (
                    generate_test as _gen_template,
                )

                code = _gen_template(
                    path=path,
                    method=method,
                    operation=operation or {},
                    schemas=schemas or {},
                    scenario=scenario,
                    instruction=instruction,
                )
                self.log.info(
                    "template generator produced fallback code", chars=len(code)
                )
            except Exception as tmpl_err:
                self.log.error("template generator also failed", error=str(tmpl_err))
                return GenerateOutput(
                    scenario_id=mutation_id,
                    test_code="",
                    status=Status.FAILED,
                    errors=[StageError(code="GENERATE_FAILED", detail=str(tmpl_err))],
                    metadata=StageMeta(stage="GENERATE", duration_ms=0),
                )

        if not isinstance(code, str) or not code.strip():
            return GenerateOutput(
                scenario_id=mutation_id,
                test_code="",
                status=Status.FAILED,
                errors=[
                    StageError(
                        code="GENERATE_EMPTY", detail="Generator produced empty output"
                    )
                ],
                metadata=StageMeta(stage="GENERATE", duration_ms=0),
            )

        dt = int((time.time() - t0) * 1000)
        self.log.info("stage success", duration_ms=dt)

        if cache_hash:
            cache.put(cache_hash, code, get_settings().GEN_MODEL)

        return GenerateOutput(
            scenario_id=mutation_id,
            test_code=code,
            imports=["@playwright/test"] if source_type in ("graphql", "grpc") else ["@playwright/test", "../client"],
            status=Status.OK,
            metadata=StageMeta(stage="GENERATE", duration_ms=dt),
            endpoint=path,
            method=method.upper() if method else None,
        )
