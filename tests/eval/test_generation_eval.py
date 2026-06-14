"""
CHERENKOV generation quality eval harness.
Authority: v3.1 + delta.

Golden-set tests that verify the core generation pipeline produces structurally
correct, spec-grounded Playwright TypeScript tests — without requiring a live
LLM (uses the deterministic template-generator fallback so CI stays fast).

Each test maps to a concrete research recommendation:

  eval_enrichment_*  → Recommendation 2 (RESTGPT spec enhancement)
  eval_template_*    → Recommendation 1 (assured generation: structure filter)
  eval_metrics_*     → Recommendation 1 (LlamaRestTest-aligned metric tracking)
  eval_finetune_*    → fine-tune signal collection

Running these tests in CI gives a baseline pass/fail signal. Run them locally
against a live Ollama to get real coverage numbers in GenMetricsStore.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest
import yaml

# ── fixtures ───────────────────────────────────────────────────────────────────

GOLDEN_SPEC_PATH = Path(__file__).parent / "golden_specs" / "simple_crud.yaml"


@pytest.fixture(scope="module")
def golden_spec() -> dict:
    with open(GOLDEN_SPEC_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def crud_schemas(golden_spec) -> dict:
    return golden_spec.get("components", {}).get("schemas", {})


@pytest.fixture(scope="module")
def post_users_op(golden_spec) -> dict:
    return golden_spec["paths"]["/users"]["post"]


@pytest.fixture(scope="module")
def get_user_op(golden_spec) -> dict:
    return golden_spec["paths"]["/users/{id}"]["get"]


@pytest.fixture(scope="module")
def list_items_op(golden_spec) -> dict:
    return golden_spec["paths"]["/items"]["get"]


# ── enrichment tests ───────────────────────────────────────────────────────────


class TestSpecEnrichment:
    """Eval: RESTGPT-style spec enrichment on the golden spec."""

    def test_enriches_post_users_operation(self, post_users_op, crud_schemas):
        from cherenkov.stages.enrich import SpecEnrichStage

        result = SpecEnrichStage().enrich("/users", "post", post_users_op, crud_schemas)
        assert (
            not result.is_empty()
        ), "POST /users has rich descriptions — enrichment should produce output"

    def test_extracts_rfc_email_rule(self, post_users_op, crud_schemas):
        from cherenkov.stages.enrich import SpecEnrichStage

        result = SpecEnrichStage().enrich("/users", "post", post_users_op, crud_schemas)
        # The operation description says "must be a valid RFC 5322 address"
        rules_text = " ".join(result.rules).lower()
        assert "rfc" in rules_text or "email" in rules_text

    def test_extracts_password_length_rule(self, post_users_op, crud_schemas):
        from cherenkov.stages.enrich import SpecEnrichStage

        result = SpecEnrichStage().enrich("/users", "post", post_users_op, crud_schemas)
        rules_text = " ".join(result.rules).lower()
        assert "8" in rules_text or "characters" in rules_text or "length" in rules_text

    def test_extracts_email_example_value(self, post_users_op, crud_schemas):
        from cherenkov.stages.enrich import SpecEnrichStage

        result = SpecEnrichStage().enrich("/users", "post", post_users_op, crud_schemas)
        assert "email" in result.body_examples
        assert "@" in str(result.body_examples["email"])

    def test_extracts_password_minlength_hint(self, post_users_op, crud_schemas):
        from cherenkov.stages.enrich import SpecEnrichStage

        result = SpecEnrichStage().enrich("/users", "post", post_users_op, crud_schemas)
        hints = result.body_hints.get("password", [])
        assert any("8" in h for h in hints), f"Expected minLength=8 hint, got: {hints}"

    def test_extracts_limit_param_example(self, list_items_op, crud_schemas):
        from cherenkov.stages.enrich import SpecEnrichStage

        result = SpecEnrichStage().enrich("/items", "get", list_items_op, crud_schemas)
        assert "limit" in result.param_examples
        assert result.param_examples["limit"] == 10  # example value from spec

    def test_extracts_limit_range_hints(self, list_items_op, crud_schemas):
        from cherenkov.stages.enrich import SpecEnrichStage

        result = SpecEnrichStage().enrich("/items", "get", list_items_op, crud_schemas)
        hints = result.body_hints.get("limit", [])
        hint_text = " ".join(hints)
        assert "1" in hint_text and "100" in hint_text

    def test_extracts_path_param_example(self, get_user_op, crud_schemas):
        from cherenkov.stages.enrich import SpecEnrichStage

        result = SpecEnrichStage().enrich(
            "/users/{id}", "get", get_user_op, crud_schemas
        )
        assert "id" in result.param_examples
        assert "usr_" in str(result.param_examples["id"])

    def test_render_prompt_block_contains_rules(self, post_users_op, crud_schemas):
        from cherenkov.stages.enrich import SpecEnrichStage

        result = SpecEnrichStage().enrich("/users", "post", post_users_op, crud_schemas)
        block = result.render_prompt_block()
        assert "SPEC RULES" in block

    def test_render_prompt_block_contains_examples(self, post_users_op, crud_schemas):
        from cherenkov.stages.enrich import SpecEnrichStage

        result = SpecEnrichStage().enrich("/users", "post", post_users_op, crud_schemas)
        block = result.render_prompt_block()
        assert "EXAMPLE" in block


# ── template generator tests (assured-generation baseline) ────────────────────


class TestTemplateGenerator:
    """Eval: deterministic template generator produces spec-correct Playwright tests."""

    def _generate(
        self,
        path: str,
        method: str,
        operation: dict,
        schemas: dict,
        case_type: str,
        expected_status: int,
    ) -> str:
        from cherenkov.ai.template_generator import generate_test
        from cherenkov.core.contracts import Scenario

        sc = Scenario(
            endpoint=path,
            method=method.upper(),
            case_type=case_type,
            mutation_id=f"{case_type}_test",
            expected_status=expected_status,
        )
        return generate_test(
            path=path,
            method=method,
            operation=operation,
            schemas=schemas,
            scenario=sc,
            instruction="",
        )

    def test_post_users_happy_path_has_imports(self, post_users_op, crud_schemas):
        code = self._generate(
            "/users", "post", post_users_op, crud_schemas, "happy_path", 201
        )
        assert "from '@playwright/test'" in code or 'from "@playwright/test"' in code
        assert "from '../client'" in code or 'from "../client"' in code

    def test_post_users_happy_path_asserts_status(self, post_users_op, crud_schemas):
        code = self._generate(
            "/users", "post", post_users_op, crud_schemas, "happy_path", 201
        )
        assert "201" in code, f"Expected 201 assertion in:\n{code}"
        assert "toBe" in code

    def test_post_users_happy_path_uses_openapi_fetch_client(
        self, post_users_op, crud_schemas
    ):
        code = self._generate(
            "/users", "post", post_users_op, crud_schemas, "happy_path", 201
        )
        assert re.search(r"client\.(POST|GET|PUT|DELETE|PATCH)", code)

    def test_post_users_validation_asserts_4xx(self, post_users_op, crud_schemas):
        code = self._generate(
            "/users", "post", post_users_op, crud_schemas, "validation", 400
        )
        assert re.search(r"toBe\((400|422)\)", code), f"Expected 4xx in:\n{code}"

    def test_get_user_happy_path_asserts_200(self, get_user_op, crud_schemas):
        code = self._generate(
            "/users/{id}", "get", get_user_op, crud_schemas, "happy_path", 200
        )
        assert "200" in code

    def test_no_raw_fetch_in_output(self, post_users_op, crud_schemas):
        code = self._generate(
            "/users", "post", post_users_op, crud_schemas, "happy_path", 201
        )
        # Must not use raw fetch() or axios
        assert "fetch(" not in code or "openapi-fetch" in code.lower()

    def test_no_markdown_fences_in_output(self, post_users_op, crud_schemas):
        code = self._generate(
            "/users", "post", post_users_op, crud_schemas, "happy_path", 201
        )
        assert "```" not in code


# ── ingest + plan integration ──────────────────────────────────────────────────


class TestIngestOnGoldenSpec:
    """Eval: IngestStage produces correct mutation menus from the golden spec."""

    def test_ingest_finds_all_three_operations(self):
        from cherenkov.stages.ingest import IngestStage

        result = IngestStage().run(str(GOLDEN_SPEC_PATH))
        assert result.status.value == "ok"
        paths = {ep.path for ep in result.endpoints}
        assert "/users" in paths
        assert "/users/{id}" in paths
        assert "/items" in paths

    def test_post_users_has_required_field_mutations(self):
        from cherenkov.stages.ingest import IngestStage

        result = IngestStage().run(str(GOLDEN_SPEC_PATH))
        post_ep = next(
            (
                ep
                for ep in result.endpoints
                if ep.path == "/users" and ep.method == "POST"
            ),
            None,
        )
        assert post_ep is not None
        mut_ids = {m.id for m in post_ep.mutations}
        # Required fields: email, password
        assert "missing_email" in mut_ids
        assert "missing_password" in mut_ids

    def test_get_items_has_happy_path_and_auth(self):
        from cherenkov.stages.ingest import IngestStage

        result = IngestStage().run(str(GOLDEN_SPEC_PATH))
        items_ep = next((ep for ep in result.endpoints if ep.path == "/items"), None)
        assert items_ep is not None
        mut_ids = {m.id for m in items_ep.mutations}
        assert "happy_path" in mut_ids
        assert "unauthorized" in mut_ids

    def test_post_users_expected_status_201(self):
        from cherenkov.stages.ingest import IngestStage

        result = IngestStage().run(str(GOLDEN_SPEC_PATH))
        post_ep = next(
            (
                ep
                for ep in result.endpoints
                if ep.path == "/users" and ep.method == "POST"
            ),
            None,
        )
        happy = next((m for m in post_ep.mutations if m.id == "happy_path"), None)
        assert happy is not None and happy.expected_status == 201


# ── GenMetricsStore integration ────────────────────────────────────────────────


class TestGenMetricsWithGoldenSpec:
    """Eval: GenMetricsStore correctly tracks a simulated pipeline run."""

    def test_full_run_metrics_tracked(self):
        from cherenkov.governance.gen_metrics import RunGenMetrics, GenMetricsStore
        from cherenkov.stages.ingest import IngestStage

        ingest = IngestStage().run(str(GOLDEN_SPEC_PATH))
        with tempfile.TemporaryDirectory() as tmp:
            store = GenMetricsStore(db_path=str(Path(tmp) / "eval.db"))
            metrics = RunGenMetrics(run_id="eval-golden")

            all_ep: set[str] = set()
            passed_ep: set[str] = set()
            for ep in ingest.endpoints:
                for mut in ep.mutations:
                    key = f"{ep.method} {ep.path}"
                    all_ep.add(key)
                    # Simulate happy_path always passes, others fail
                    ok = mut.case_type == "happy_path"
                    metrics.record_generation(all_gates_passed=ok)
                    if ok:
                        passed_ep.add(key)
            for ep_key in all_ep:
                metrics.record_operation(covered=(ep_key in passed_ep))

            store.save(metrics)
            rows = store.history()
            assert len(rows) == 1
            assert rows[0]["run_id"] == "eval-golden"
            assert rows[0]["total_generated"] > 0
            assert rows[0]["operations_total"] == len(all_ep)

    def test_gate_pass_rate_reflects_happy_path_only(self):
        from cherenkov.governance.gen_metrics import RunGenMetrics
        from cherenkov.stages.ingest import IngestStage

        ingest = IngestStage().run(str(GOLDEN_SPEC_PATH))
        metrics = RunGenMetrics(run_id="eval-rate")
        for ep in ingest.endpoints:
            for mut in ep.mutations:
                ok = mut.case_type == "happy_path"
                metrics.record_generation(all_gates_passed=ok)

        # happy_path count / total should be between 0 and 1
        assert 0.0 < metrics.gate_pass_rate < 1.0

    def test_trend_summary_after_eval_run(self):
        import tempfile
        from cherenkov.governance.gen_metrics import RunGenMetrics, GenMetricsStore

        with tempfile.TemporaryDirectory() as tmp:
            store = GenMetricsStore(db_path=str(Path(tmp) / "eval.db"))
            m = RunGenMetrics(run_id="trend-test")
            for _ in range(5):
                m.record_generation(all_gates_passed=True)
            store.save(m)
            summary = store.trend_summary()
            assert "trend-test" in summary


# ── FinetuneLogger integration ────────────────────────────────────────────────


class TestFinetuneLogger:
    """Eval: FinetuneLogger captures accepted/rejected outcomes."""

    def test_logs_accepted_record(self):
        from cherenkov.governance.finetune_log import FinetuneLogger

        with tempfile.TemporaryDirectory() as tmp:
            logger = FinetuneLogger(log_path=str(Path(tmp) / "ft.jsonl"))
            logger.log_outcome(
                run_id="r1",
                endpoint="/users",
                method="POST",
                case_type="happy_path",
                mutation_id="happy_path",
                verdict="accepted",
                quality_score=0.95,
                gate_results=[{"gate": "syntax", "passed": True, "detail": "ok"}],
                test_code="import { test } from '@playwright/test';",
            )
            records = logger.tail(n=5)
            assert len(records) == 1
            assert records[0]["verdict"] == "accepted"
            assert records[0]["endpoint"] == "POST /users"

    def test_logs_rejected_record(self):
        from cherenkov.governance.finetune_log import FinetuneLogger

        with tempfile.TemporaryDirectory() as tmp:
            logger = FinetuneLogger(log_path=str(Path(tmp) / "ft.jsonl"))
            logger.log_outcome(
                run_id="r2",
                endpoint="/users",
                method="POST",
                case_type="validation",
                mutation_id="missing_email",
                verdict="rejected",
                quality_score=0.5,
                gate_results=[{"gate": "syntax", "passed": False, "detail": "empty"}],
                test_code="",
            )
            stats = logger.stats()
            assert stats["rejected"] == 1
            assert stats["accepted"] == 0

    def test_stats_accept_rate(self):
        from cherenkov.governance.finetune_log import FinetuneLogger

        with tempfile.TemporaryDirectory() as tmp:
            logger = FinetuneLogger(log_path=str(Path(tmp) / "ft.jsonl"))
            for _ in range(3):
                logger.log_outcome(
                    run_id="r",
                    endpoint="/x",
                    method="GET",
                    case_type="happy_path",
                    mutation_id="hp",
                    verdict="accepted",
                    quality_score=1.0,
                    gate_results=[],
                    test_code="code",
                )
            logger.log_outcome(
                run_id="r",
                endpoint="/x",
                method="GET",
                case_type="validation",
                mutation_id="v",
                verdict="rejected",
                quality_score=0.3,
                gate_results=[],
                test_code="",
            )
            stats = logger.stats()
            assert stats["total"] == 4
            assert stats["accept_rate"] == pytest.approx(0.75)

    def test_empty_log_returns_empty_tail(self):
        from cherenkov.governance.finetune_log import FinetuneLogger

        with tempfile.TemporaryDirectory() as tmp:
            logger = FinetuneLogger(log_path=str(Path(tmp) / "ft.jsonl"))
            assert logger.tail() == []

    def test_missing_log_file_returns_zero_stats(self):
        from cherenkov.governance.finetune_log import FinetuneLogger

        with tempfile.TemporaryDirectory() as tmp:
            logger = FinetuneLogger(log_path=str(Path(tmp) / "nonexistent.jsonl"))
            assert logger.stats()["total"] == 0
