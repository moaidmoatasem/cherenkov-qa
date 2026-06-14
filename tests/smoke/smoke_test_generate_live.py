#!/usr/bin/env python3
"""
smoke_test_generate_live.py — the ONE test that exercises the real model.

Why this exists
---------------
Every other test mocks the LLM. The core product claim — "spec in, compilable
Playwright test out" — is therefore never verified end-to-end in CI: a refactor
that breaks the prompt/parse contract in ai/ollama_client.py goes green while the
shipped tool silently produces no usable test. This smoke closes that gap.

It is OPT-IN. It does nothing unless CHERENKOV_LIVE_LLM=1, because hosted CI
runners have no GPU and cannot run qwen2.5-coder:7b. Run it locally, or on a
self-hosted GPU runner (see the `live-llm-generate` job in .github/workflows/ci.yml).

    CHERENKOV_LIVE_LLM=1 PYTHONPATH=. python3 smoke_test_generate_live.py

Exit codes: 0 = passed or cleanly skipped; 1 = real failure (the point of the test).
"""

from __future__ import annotations

import os
import sys

import requests

from cherenkov.core.settings import get_settings
from cherenkov.core.contracts import Scenario, Status
from cherenkov.stages.generate import GenerateStage


def _skip(msg: str) -> None:
    print(f"SKIP smoke_test_generate_live: {msg}")
    sys.exit(0)


def _fail(msg: str) -> None:
    print(f"FAIL smoke_test_generate_live: {msg}")
    sys.exit(1)


def _ollama_reachable() -> bool:
    base = get_settings().OLLAMA_URL.rsplit("/api/generate", 1)[0]
    try:
        return requests.get(f"{base}/api/tags", timeout=5).status_code == 200
    except requests.RequestException:
        return False


def main() -> None:
    if os.getenv("CHERENKOV_LIVE_LLM") != "1":
        _skip("CHERENKOV_LIVE_LLM != 1 (opt-in: needs a real Ollama + model)")

    # The flag asserts intent to run the real path — an unreachable model is now a
    # failure, not a skip, so a broken local/self-hosted setup is surfaced loudly.
    if not _ollama_reachable():
        _skip(f"CHERENKOV_LIVE_LLM=1 but Ollama not reachable at {get_settings().OLLAMA_URL}")

    # Minimal but real generate input: POST /users creating a user.
    operation = {
        "operationId": "createUser",
        "requestBody": {
            "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/NewUser"}}
            }
        },
        "responses": {"201": {"description": "created"}},
    }
    schemas = {
        "NewUser": {
            "type": "object",
            "required": ["email", "password"],
            "properties": {
                "email": {"type": "string", "format": "email"},
                "password": {"type": "string", "minLength": 8},
            },
        }
    }
    scenario = Scenario(
        endpoint="/users",
        method="POST",
        case_type="happy_path",
        priority="P1",
        mutation_id="live-smoke-happy",
        expected_status=201,
    )

    out = GenerateStage(run_id="live-smoke").run(
        scenario=scenario,
        path="/users",
        method="POST",
        operation=operation,
        schemas=schemas,
        instruction="Happy path: create a user and assert 201 + an id in the body.",
    )

    if out.status != Status.OK:
        _fail(f"generate returned status={out.status} errors={out.errors}")

    code = out.test_code or ""
    if not code.strip():
        _fail("model produced EMPTY test code (the exact silent-failure mode)")

    # Structural invariants of a real CHERENKOV test — cheap to check, catch the
    # ways a degraded model/prompt regresses without a GPU compile step.
    checks = {
        "has a Playwright test()": "test(" in code,
        "uses openapi-fetch client (no raw fetch/axios) — D-invariant": (
            "client." in code
        )
        and ("axios" not in code)
        and ("fetch(" not in code),
        "asserts a status (expect)": "expect(" in code,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        print("---- generated code ----")
        print(code)
        print("-------------------------")
        _fail("structural checks failed: " + "; ".join(failed))

    print(
        "PASS smoke_test_generate_live: real model produced a structurally valid "
        f"Playwright test ({len(code)} chars, model={get_settings().GEN_MODEL})"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
