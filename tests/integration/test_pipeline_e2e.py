"""
Integration test: full pipeline smoke (no live LLM, no live Playwright).

Exercises the real code path:
  OpenAPI spec file
    → IngestStage (real YAML parse + endpoint slicing)
    → PlanStage (real scenario selection)
    → GenerateStage (LLM substrate mocked → returns canned TypeScript)
    → ValidationEngine.validate_suite (PlaywrightRunner mocked → returns pass/fail)

Verifies:
  - Each stage produces the expected contract types
  - Scenario count is plausible for the petstore fixture
  - generate output contains TypeScript boilerplate
  - ValidationEngine returns a well-formed result dict
  - The full dict has "status" and "reports" keys consumed by the CLI
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PETSTORE_YAML = Path(__file__).parent.parent.parent / "bench" / "fixtures" / "petstore.yaml"

CANNED_TS = textwrap.dedent("""\
    import { client } from '../client';
    import { test, expect } from '@playwright/test';

    test('list pets happy path', async () => {
      const { data, response } = await client.GET('/pets');
      expect(response.status).toBe(200);
      expect(Array.isArray(data)).toBe(true);
    });
""")


# ── Stage-level tests ─────────────────────────────────────────────────────────

class TestIngestStage:
    def test_petstore_produces_endpoints(self):
        from cherenkov.stages.ingest import IngestStage
        from cherenkov.core.contracts import Status

        out = IngestStage().run(str(PETSTORE_YAML))

        assert out.status == Status.OK
        assert len(out.endpoints) >= 2, "petstore has at least /pets and /pets/{petId}"

    def test_endpoints_have_method_and_path(self):
        from cherenkov.stages.ingest import IngestStage

        out = IngestStage().run(str(PETSTORE_YAML))

        for ep in out.endpoints:
            assert ep.method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
            assert ep.path.startswith("/")

    def test_missing_spec_raises(self, tmp_path):
        from cherenkov.stages.ingest import IngestStage
        from cherenkov.core.contracts import Status

        out = IngestStage().run(str(tmp_path / "nonexistent.yaml"))
        assert out.status == Status.FAILED


class TestPlanStage:
    def _ingest(self):
        from cherenkov.stages.ingest import IngestStage
        return IngestStage().run(str(PETSTORE_YAML))

    def test_plan_succeeds(self):
        from cherenkov.stages.plan import PlanStage
        from cherenkov.core.contracts import Status

        plan = PlanStage().run(self._ingest())
        assert plan.status == Status.OK

    def test_plan_produces_scenarios(self):
        from cherenkov.stages.plan import PlanStage

        plan = PlanStage().run(self._ingest())
        assert len(plan.scenarios) >= 3, "petstore should yield ≥3 test scenarios"

    def test_scenarios_have_required_fields(self):
        from cherenkov.stages.plan import PlanStage

        plan = PlanStage().run(self._ingest())
        for sc in plan.scenarios:
            assert sc.endpoint
            assert sc.method
            assert sc.case_type
            assert isinstance(sc.expected_status, int)
            assert 100 <= sc.expected_status < 600

    def test_failed_ingest_propagates(self):
        from cherenkov.stages.plan import PlanStage
        from cherenkov.core.contracts import Status, IngestOutput, StageMeta

        bad_ingest = IngestOutput(
            endpoints=[],
            client_stub_path="",
            status=Status.FAILED,
            errors=[],
            metadata=StageMeta(stage="INGEST", duration_ms=0),
        )
        plan = PlanStage().run(bad_ingest)
        assert plan.status == Status.FAILED
        assert len(plan.scenarios) == 0


class TestGenerateStageMocked:
    def _get_first_scenario(self):
        from cherenkov.stages.ingest import IngestStage
        from cherenkov.stages.plan import PlanStage

        ingest = IngestStage().run(str(PETSTORE_YAML))
        plan = PlanStage().run(ingest)
        return plan.scenarios[0], ingest

    def test_generate_with_mocked_llm(self):
        from cherenkov.stages.generate import GenerateStage
        from cherenkov.core.contracts import Status

        sc, ingest = self._get_first_scenario()
        ep = next(e for e in ingest.endpoints if e.method == sc.method and e.path == sc.endpoint)

        mock_client = MagicMock()
        mock_client.generate.return_value = CANNED_TS

        with patch("cherenkov.stages.generate.get_client", return_value=mock_client):
            out = GenerateStage("test-run").run(
                scenario=sc,
                path=ep.path,
                method=ep.method,
                operation=getattr(ep, "operation", {}),
                schemas=getattr(ep, "schemas", {}),
                instruction=f"{sc.case_type} test for {sc.method} {sc.endpoint}",
            )

        assert out.status == Status.OK
        assert "import" in out.test_code
        assert "test(" in out.test_code

    def test_generate_llm_error_falls_back_to_template(self):
        """GenerateStage has a template fallback — LLM errors yield OK with template code."""
        from cherenkov.stages.generate import GenerateStage
        from cherenkov.core.contracts import Status

        sc, _ = self._get_first_scenario()

        mock_client = MagicMock()
        mock_client.generate.side_effect = RuntimeError("LLM unavailable")

        with patch("cherenkov.stages.generate.get_client", return_value=mock_client):
            out = GenerateStage("test-run").run(scenario=sc)

        # Fallback template produces valid (if minimal) TypeScript
        assert out.status == Status.OK
        assert out.test_code  # non-empty


class TestValidationEngineMocked:
    def test_validate_suite_with_mocked_playwright(self, tmp_path):
        from cherenkov.execution.validate import ValidationEngine

        # Write a minimal fake test file so the engine finds something to run
        tests_dir = tmp_path / "generated_tests"
        tests_dir.mkdir()
        fake_test = tests_dir / "list_pets_happy_path.spec.ts"
        fake_test.write_text(CANNED_TS)

        mock_runner_result = {
            "passed": True,
            "trace_path": "",
            "scenario_id": "list_pets_happy_path",
        }

        with (
            patch("cherenkov.execution.validate.PlaywrightRunner") as MockRunner,
            patch.object(
                __import__("cherenkov.execution.validate", fromlist=["ValidationEngine"]).ValidationEngine,
                "stub_dir",
                new=str(tmp_path),
                create=True,
            ),
        ):
            MockRunner.return_value.execute_test.return_value = mock_runner_result
            engine = ValidationEngine("test-pipe")
            engine.stub_dir = str(tmp_path)
            engine.tests_dir = str(tests_dir)

            result = engine.validate_suite("http://localhost:9999", workers=1)

        assert "status" in result
        assert "reports" in result
        assert isinstance(result["reports"], list)

    def test_validate_suite_empty_dir(self, tmp_path):
        from cherenkov.execution.validate import ValidationEngine

        engine = ValidationEngine("test-empty")
        engine.stub_dir = str(tmp_path)
        engine.tests_dir = str(tmp_path / "generated_tests")

        result = engine.validate_suite("http://localhost:9999")
        assert result["status"] in ("empty", "done", "error")


# ── Full pipeline smoke ───────────────────────────────────────────────────────

class TestFullPipelineSmoke:
    """Ingest → Plan → Generate (mocked LLM) → validate_suite (mocked Playwright)."""

    def test_end_to_end(self, tmp_path):
        from cherenkov.stages.ingest import IngestStage
        from cherenkov.stages.plan import PlanStage
        from cherenkov.stages.generate import GenerateStage
        from cherenkov.execution.validate import ValidationEngine
        from cherenkov.core.contracts import Status

        # Stage 1: Ingest
        ingest_out = IngestStage().run(str(PETSTORE_YAML))
        assert ingest_out.status == Status.OK
        assert ingest_out.endpoints

        # Stage 2: Plan
        plan_out = PlanStage().run(ingest_out)
        assert plan_out.status == Status.OK
        assert plan_out.scenarios

        # Stage 3: Generate (mock LLM)
        tests_dir = tmp_path / "generated_tests"
        tests_dir.mkdir()

        mock_client = MagicMock()
        mock_client.generate.return_value = CANNED_TS

        generated = 0
        # GenerateStage falls back to a template when LLM is unavailable —
        # patching get_client to raise ensures the template path is exercised.
        mock_client = MagicMock()
        mock_client.generate.side_effect = RuntimeError("no llm in test env")

        with patch("cherenkov.stages.generate.get_client", return_value=mock_client):
            gen = GenerateStage("smoke")
            for sc in plan_out.scenarios:
                ep = next(
                    (e for e in ingest_out.endpoints if e.path == sc.endpoint and e.method == sc.method),
                    None,
                )
                out = gen.run(
                    scenario=sc,
                    path=sc.endpoint,
                    method=sc.method,
                    operation=getattr(ep, "operation", {}) if ep else {},
                    schemas=getattr(ep, "schemas", {}) if ep else {},
                    instruction=f"{sc.case_type} for {sc.method} {sc.endpoint}",
                )
                if out.status == Status.OK and out.test_code:
                    fname = f"{sc.mutation_id}.spec.ts"
                    (tests_dir / fname).write_text(out.test_code)
                    generated += 1

        assert generated >= 1, "at least one test file should be generated"

        # Stage 4: Validate (mock Playwright)
        engine = ValidationEngine("smoke")
        engine.stub_dir = str(tmp_path)
        engine.tests_dir = str(tests_dir)

        with patch("cherenkov.execution.validate.PlaywrightRunner") as MockRunner:
            MockRunner.return_value.execute_test.return_value = {
                "passed": True,
                "trace_path": "",
                "scenario_id": "smoke",
            }
            result = engine.validate_suite("http://localhost:9999", workers=1)

        assert result["status"] in ("done", "ok", "passed", "empty", "success")
        assert isinstance(result.get("reports", []), list)
        total = len(result.get("reports", []))
        passed = sum(1 for r in result.get("reports", []) if r.get("passed"))
        assert passed == total, f"expected all {total} tests to pass with mocked Playwright"
