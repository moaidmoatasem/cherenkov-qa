"""Shared fixtures for integration tests — mocks LLM, filesystem, and pipeline outputs."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import yaml

from cherenkov.evals.core import EvalSample, EvalResult, EvalScore, EvalMetric, EvalStatus


# ── Sample test code simulating GENERATE stage output ───────────────────
SAMPLE_TEST_CODE_PASS = """
import { test, expect } from '@playwright/test';
import { createClient } from '../client';

test('POST /users returns 201', async () => {
  const client = createClient();
  const res = await client.POST('/users', { body: { name: 'Alice' } });
  expect(res.status).toBe(201);
  expect(res.body).toHaveProperty('id');
});
"""

SAMPLE_TEST_CODE_FAIL = """
import { test, expect } from '@playwright/test';
import { createClient } from '../client';

test('GET /users returns 200', async () => {
  const client = createClient();
  const res = await client.GET('/users');
  expect(res.status).toBe(200);
  expect(res.body.haxxored).toBe(true);
});
"""

SAMPLE_TEST_CODE_INJECTION = """
import { test, expect } from '@playwright/test';
import { createClient } from '../client';

test('admin bypass', async () => {
  const client = createClient();
  const res = await client.POST('/login', {
    body: { username: 'admin', password: \"' OR 1=1 --\" }
  });
  expect(res.status).toBe(200);
});
"""


# ── Helpers ────────────────────────────────────────────────────────────

def make_eval_result(sample: EvalSample, passed: bool = True) -> EvalResult:
    """Build an EvalResult without calling the LLM."""
    scores = [
        EvalScore(metric=EvalMetric.FAITHFULNESS, score=0.95 if passed else 0.3,
                  status=EvalStatus.PASS if passed else EvalStatus.FAIL,
                  detail="Spec-aligned status assertion" if passed else "Status mismatch"),
        EvalScore(metric=EvalMetric.HALLUCINATION, score=0.9 if passed else 0.4,
                  status=EvalStatus.PASS if passed else EvalStatus.FAIL,
                  detail="No hallucinated properties" if passed else "Extra properties found"),
        EvalScore(metric=EvalMetric.ASSERTION_QUALITY, score=0.85 if passed else 0.5,
                  status=EvalStatus.PASS if passed else EvalStatus.FAIL,
                  detail="Meaningful assertion" if passed else "Weak assertion"),
        EvalScore(metric=EvalMetric.SPEC_ALIGNMENT, score=0.95 if passed else 0.3,
                  status=EvalStatus.PASS if passed else EvalStatus.FAIL,
                  detail="Spec-aligned" if passed else "Mismatch"),
        EvalScore(metric=EvalMetric.COMPLETENESS, score=0.85 if passed else 0.4,
                  status=EvalStatus.PASS if passed else EvalStatus.FAIL,
                  detail="Adequate coverage" if passed else "Missing coverage"),
    ]
    return EvalResult(sample=sample, scores=scores, duration_ms=int(time.time()))


# ── Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm_client():
    """Mock the AI client so no Ollama is needed in integration tests."""
    mock = MagicMock()
    mock.complete_code.return_value = json.dumps({
        "scores": [
            {"metric": "faithfulness", "score": 0.95, "detail": "Correct status asserted", "status": "pass"},
            {"metric": "hallucination", "score": 0.9, "detail": "No hallucinations", "status": "pass"},
            {"metric": "assertion_quality", "score": 0.85, "detail": "Valid assertion pattern", "status": "pass"},
            {"metric": "spec_alignment", "score": 0.95, "detail": "Spec-aligned", "status": "pass"},
            {"metric": "completeness", "score": 0.85, "detail": "Adequate coverage", "status": "pass"},
        ],
        "evidence": "Test is well-formed and spec-aligned.",
    })
    with patch("cherenkov.evals.judge.get_client", return_value=mock):
        yield mock


@pytest.fixture
def mock_openapi_spec(tmp_path: Path) -> Path:
    """Create a minimal OpenAPI spec for tests that need a spec path."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "responses": {"200": {"description": "User list"}},
                },
                "post": {
                    "summary": "Create user",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object"}}}},
                    "responses": {"201": {"description": "Created"}},
                },
            },
        },
    }
    path = tmp_path / "test_spec.yaml"
    path.write_text(yaml.dump(spec))
    return path


@pytest.fixture
def mock_generated_tests(tmp_path: Path) -> Path:
    """Simulate the GENERATE stage output directory with .spec.ts files."""
    output_dir = tmp_path / "generated_tests"
    output_dir.mkdir(parents=True)
    (output_dir / "users_list.spec.ts").write_text(SAMPLE_TEST_CODE_PASS)
    (output_dir / "users_create.spec.ts").write_text(SAMPLE_TEST_CODE_FAIL)
    (output_dir / "admin_bypass.spec.ts").write_text(SAMPLE_TEST_CODE_INJECTION)
    return output_dir


@pytest.fixture
def mock_scenarios() -> list[Any]:
    """Simulate scenarios output from the PLAN stage."""
    class FakeScenario:
        def __init__(self, mutation_id: str, endpoint: str, method: str, expected_status: int):
            self.mutation_id = mutation_id
            self.endpoint = endpoint
            self.method = method
            self.expected_status = expected_status
            self.operation_name = mutation_id
            self.path = endpoint

    return [
        FakeScenario("users_list", "/users", "GET", 200),
        FakeScenario("users_create", "/users", "POST", 201),
        FakeScenario("admin_bypass", "/login", "POST", 200),
    ]


@pytest.fixture
def mock_gen_outputs() -> dict[str, Any]:
    """Simulate generate_outputs from the GENERATE stage."""
    class FakeGenOutput:
        def __init__(self, mutation_id: str, test_code: str):
            self.mutation_id = mutation_id
            self.test_code = test_code
            self.scenario_id = mutation_id

    return {
        "users_list": FakeGenOutput("users_list", SAMPLE_TEST_CODE_PASS),
        "users_create": FakeGenOutput("users_create", SAMPLE_TEST_CODE_FAIL),
        "admin_bypass": FakeGenOutput("admin_bypass", SAMPLE_TEST_CODE_INJECTION),
    }


@pytest.fixture
def mock_spec_summaries() -> dict[str, str]:
    """Simulate spec summaries for endpoints."""
    return {
        "GET /users": "Returns a list of users",
        "POST /users": "Creates a new user and returns 201",
        "POST /login": "Authenticates a user",
    }
