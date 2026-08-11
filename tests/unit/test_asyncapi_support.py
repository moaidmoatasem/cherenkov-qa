"""Unit tests for the AsyncAPI source adapter, planner, and its CLI wiring.

The adapter and planner were built and unit-testable long before anything could
reach them: `AsyncAPIScenarioPlanner` was imported nowhere, `asyncapi` was
absent from `validate --source`, and `GenerateStage` had no branch to render
`prompts/asyncapi_test.j2`. These tests cover the wiring itself, so the
capability cannot silently become unreachable again.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cherenkov.sources.asyncapi.adapter import AsyncAPISourceAdapter
from cherenkov.sources.asyncapi.contracts import AsyncAPIScenario
from cherenkov.stages.plan_asyncapi import AsyncAPIScenarioPlanner

SPEC = textwrap.dedent(
    """
    asyncapi: '2.6.0'
    info:
      title: Orders Service
      version: '1.0.0'
    channels:
      order/created:
        publish:
          message:
            $ref: '#/components/messages/OrderCreated'
      order/shipped:
        subscribe:
          message:
            name: OrderShipped
            payload:
              type: object
              required: [orderId, carrier]
              properties:
                orderId: { type: string }
                carrier: { type: string }
    components:
      messages:
        OrderCreated:
          name: OrderCreated
          contentType: application/json
          payload:
            type: object
            required: [orderId, customerId, total]
            properties:
              orderId: { type: string }
              customerId: { type: string }
              total: { type: number }
    """
)


@pytest.fixture
def spec_file(tmp_path: Path) -> str:
    path = tmp_path / "orders.yaml"
    path.write_text(SPEC, encoding="utf-8")
    return str(path)


# ── Adapter ──────────────────────────────────────────────────────────────────


def test_adapter_yields_publish_and_subscribe_operations(spec_file):
    ops = list(AsyncAPISourceAdapter(spec_file).iter_operations())
    assert {(o.channel, o.operation) for o in ops} == {
        ("order/created", "publish"),
        ("order/shipped", "subscribe"),
    }


def test_adapter_resolves_message_ref(spec_file):
    """A $ref'd message must resolve to its payload, not an empty dict."""
    ops = {o.channel: o for o in AsyncAPISourceAdapter(spec_file).iter_operations()}
    created = ops["order/created"]
    assert created.message_name == "OrderCreated"
    assert created.payload_schema is not None
    assert created.payload_schema["required"] == ["orderId", "customerId", "total"]


def test_adapter_reads_inline_payload(spec_file):
    ops = {o.channel: o for o in AsyncAPISourceAdapter(spec_file).iter_operations()}
    assert ops["order/shipped"].payload_schema["required"] == ["orderId", "carrier"]


def test_adapter_ignores_channels_without_operations(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("asyncapi: '2.6.0'\nchannels:\n  noop: {}\n", encoding="utf-8")
    assert list(AsyncAPISourceAdapter(str(path)).iter_operations()) == []


# ── Planner ──────────────────────────────────────────────────────────────────


def test_planner_covers_every_operation(spec_file):
    scenarios = AsyncAPIScenarioPlanner().plan(AsyncAPISourceAdapter(spec_file))
    assert {s.channel for s in scenarios} == {"order/created", "order/shipped"}


def test_planner_emits_negative_scenarios_with_distinct_statuses(spec_file):
    scenarios = AsyncAPIScenarioPlanner().plan(AsyncAPISourceAdapter(spec_file))
    created = [s for s in scenarios if s.channel == "order/created"]
    by_type = {s.scenario_type: s.expected_status for s in created}
    assert by_type == {
        "happy_path": 200,
        "missing_required": 400,
        "invalid_payload": 422,
        "auth": 401,
    }


def test_planner_carries_required_fields_through(spec_file):
    scenarios = AsyncAPIScenarioPlanner().plan(AsyncAPISourceAdapter(spec_file))
    created = next(s for s in scenarios if s.channel == "order/created")
    assert created.required_fields == ["orderId", "customerId", "total"]


def test_planner_skips_missing_required_when_no_required_fields(tmp_path):
    path = tmp_path / "loose.yaml"
    path.write_text(
        textwrap.dedent(
            """
            asyncapi: '2.6.0'
            channels:
              ping:
                publish:
                  message:
                    name: Ping
                    payload:
                      type: object
            """
        ),
        encoding="utf-8",
    )
    scenarios = AsyncAPIScenarioPlanner().plan(AsyncAPISourceAdapter(str(path)))
    assert "missing_required" not in {s.scenario_type for s in scenarios}


# ── GenerateStage branch ─────────────────────────────────────────────────────


def _scenario() -> AsyncAPIScenario:
    return AsyncAPIScenario(
        channel="order/created",
        operation="publish",
        scenario_type="happy_path",
        message="OrderCreated",
        expected_status=200,
        required_fields=["orderId", "customerId"],
    )


def test_generate_renders_asyncapi_template_into_the_prompt():
    """The asyncapi branch must render prompts/asyncapi_test.j2, not fall through
    to the OpenAPI path (which would raise TypeError on a non-Scenario)."""
    from cherenkov.stages.generate import GenerateStage

    fake = MagicMock()
    fake.complete_code.return_value = (
        "import { test, expect } from '@playwright/test';\n"
        "test('ws', async () => { expect(1).toBe(1); });"
    )
    with patch("cherenkov.stages.generate.get_client", return_value=fake):
        GenerateStage("t").run(scenario=_scenario(), source_type="asyncapi")

    assert fake.complete_code.called
    prompt = " ".join(str(a) for a in fake.complete_code.call_args[0])
    prompt += " ".join(str(v) for v in fake.complete_code.call_args[1].values())
    assert "order/created" in prompt
    assert "publish" in prompt
    assert "orderId" in prompt


def test_generate_rejects_wrong_scenario_type_for_asyncapi():
    from cherenkov.stages.generate import GenerateStage

    with pytest.raises(TypeError, match="asyncapi"):
        GenerateStage("t").run(scenario=object(), source_type="asyncapi")


# ── CLI wiring ───────────────────────────────────────────────────────────────


TARGET = ["--target", "http://localhost:8000"]


def test_validate_accepts_asyncapi_source():
    """`--source asyncapi` must be a valid choice, not an unknown-value error."""
    from cherenkov.cli.commands.validate import validate_cmd

    result = CliRunner().invoke(validate_cmd, [*TARGET, "--source", "asyncapi"])
    assert "not one of" not in result.output
    assert "invalid choice" not in result.output.lower()


def test_validate_asyncapi_requires_spec():
    from cherenkov.cli.commands.validate import validate_cmd

    result = CliRunner().invoke(validate_cmd, [*TARGET, "--source", "asyncapi"])
    assert result.exit_code == 1
    assert "--spec is required for --source asyncapi" in result.output


def test_validate_asyncapi_plans_and_generates(spec_file):
    from cherenkov.cli.commands.validate import validate_cmd

    with patch("cherenkov.stages.generate.GenerateStage.run") as mock_run:
        result = CliRunner().invoke(
            validate_cmd, [*TARGET, "--source", "asyncapi", "--spec", spec_file]
        )

    # Scoped to the AsyncAPI planning/generation phase. `validate` afterwards
    # runs the Playwright suite, which needs `stub/npm install`; that downstream
    # step is not what this test covers, so the exit code is deliberately not
    # asserted here.
    assert "Planned 8 scenarios from 2 channels" in result.output
    assert "Generated 8/8 test files" in result.output
    assert mock_run.call_count == 8
    assert all(
        call.kwargs["source_type"] == "asyncapi" for call in mock_run.call_args_list
    )
