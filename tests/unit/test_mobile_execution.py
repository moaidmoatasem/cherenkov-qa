"""
Tests for the wired mobile pipeline: source-derived planning, assertion
strength gating, and real device execution via the runner.

The load-bearing property under test is that a flow is only ever reported as
passing when it actually ran and actually asserted something.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cherenkov.sources.mobile.contracts import MobileApp, MobileFlow
from cherenkov.stages.mobile_cmd import mobile
from cherenkov.stages.mobile_generate import MobileGenerateOutput, MobileGenerateStage
from cherenkov.stages.mobile_plan import MobilePlanStage
from cherenkov.stages.mobile_review import MobileReviewStage


@pytest.fixture
def hil_file(tmp_path: Path) -> str:
    path = tmp_path / "flows.hil"
    path.write_text(
        json.dumps(
            {
                "flows": [
                    {
                        "flow_id": "checkout",
                        "name": "Checkout flow",
                        "screens": ["cart", "Order Confirmed"],
                        "actions": [
                            {"tap": "Cart"},
                            {"action": "type", "target": "card number"},
                            {
                                "action": "assert",
                                "target": "Order Confirmed",
                                "expect": "Order Confirmed",
                            },
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return str(path)


# ── Planning from a real source ──────────────────────────────────────────────


def test_plan_derives_scenarios_from_flows():
    flows = [
        MobileFlow(
            flow_id="f1",
            name="Login",
            screens=["home", "Dashboard"],
            actions=[{"tap": "Sign in"}, {"action": "assert", "target": "Dashboard"}],
        )
    ]
    out = MobilePlanStage().run(flows)
    assert out.source == "hil"
    assert len(out.scenarios) == 1
    assert out.scenarios[0].id == "f1"
    assert any(s.action == "tap" and s.target == "Sign in"
               for s in out.scenarios[0].planned_steps)


def test_plan_appends_destination_assertion_when_flow_has_none():
    """An unchecked flow gets an assertion on its recorded destination screen."""
    flows = [
        MobileFlow(
            flow_id="f2",
            name="Browse",
            screens=["home", "Product Detail"],
            actions=[{"tap": "Shoes"}],
        )
    ]
    out = MobilePlanStage().run(flows)
    verifies = [s for s in out.scenarios[0].planned_steps if s.action == "verify"]
    assert len(verifies) == 1
    assert verifies[0].expected_text == "Product Detail"


def test_plan_uses_real_app_id_from_apk():
    app = MobileApp("com.acme.shop", "Shop", "android", "2.1", "/tmp/shop.apk")
    out = MobilePlanStage().run(app)
    assert out.source == "apk"
    assert out.app_id == "com.acme.shop"
    assert out.scenarios[0].app_id == "com.acme.shop"


def test_plan_without_source_is_flagged_demo():
    out = MobilePlanStage().run()
    assert out.source == "demo"
    assert all(s.source == "demo" for s in out.scenarios)


# ── Generation emits checkable assertions ────────────────────────────────────


def test_generated_assertion_is_never_a_catch_all():
    out = MobilePlanStage().run(
        [
            MobileFlow(
                flow_id="f3",
                name="Pay",
                screens=["Receipt"],
                actions=[{"tap": "Pay"}],
            )
        ]
    )
    yaml_text = MobileGenerateStage(app_id="com.acme.shop").run(
        out.scenarios[0]
    ).yaml_content
    assert 'text: ".*"' not in yaml_text
    assert 'text: "Receipt"' in yaml_text


def test_generate_uses_supplied_app_id():
    out = MobilePlanStage().run()
    gen = MobileGenerateStage(app_id="com.acme.shop").run(out.scenarios[0])
    assert gen.yaml_content.startswith("appId: com.acme.shop")
    assert gen.app_id == "com.acme.shop"


def test_unassertable_step_is_recorded_not_papered_over():
    """A verify step with no concrete text emits no assertion, and says so."""
    out = MobilePlanStage().run()
    scenario = out.scenarios[0]
    scenario.planned_steps = []
    scenario.steps = ["verify the screen is visible"]
    gen = MobileGenerateStage().run(scenario)
    assert gen.unassertable_steps == ["verify the screen is visible"]
    assert "assertVisible" not in gen.yaml_content


# ── Integrity gate ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("expected", [".*", ".+", "*", "", "^.*$"])
def test_review_rejects_weakened_assertion(expected: str):
    yaml_text = (
        f'appId: com.acme.shop\n---\nname: t\n\n- tapOn:\n    text: "Go"\n'
        f'- assertVisible:\n    text: "{expected}"\n'
    )
    out = MobileReviewStage().run(MobileGenerateOutput("s1", yaml_text))
    assert out.passed is False
    assert any("Weakened assertion" in e for e in out.errors)


def test_review_strict_rejects_flow_with_no_assertion():
    yaml_text = 'appId: com.acme.shop\n---\nname: t\n\n- tapOn:\n    text: "Go"\n'
    strict = MobileReviewStage(strict=True).run(MobileGenerateOutput("s1", yaml_text))
    lenient = MobileReviewStage(strict=False).run(MobileGenerateOutput("s1", yaml_text))
    assert strict.passed is False
    assert lenient.passed is True
    assert any("no assertion" in w for w in lenient.warnings)


def test_review_warns_on_placeholder_app_id():
    yaml_text = (
        'appId: com.example.app\n---\nname: t\n\n- assertVisible:\n    text: "Home"\n'
    )
    out = MobileReviewStage().run(MobileGenerateOutput("s1", yaml_text))
    assert out.passed is True
    assert any("placeholder appId" in w for w in out.warnings)


# ── CLI wiring: generation, gating, execution ────────────────────────────────


def test_cli_writes_flows_and_reports_not_executed_without_runner(hil_file, tmp_path):
    out_dir = tmp_path / "flows"
    with patch(
        "cherenkov.stages.mobile_cmd.MaestroRunner.health_check", return_value=False
    ):
        result = CliRunner().invoke(
            mobile,
            [hil_file, "--app-id", "com.acme.shop", "--out", str(out_dir), "--json"],
        )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["executed"] == 0
    assert payload["flows"][0]["status"] == "not_executed"
    assert payload["flows"][0]["executed"] is False
    assert (out_dir / "checkout.yaml").exists()


def test_cli_executes_flow_and_reports_device_verdict(hil_file, tmp_path):
    out_dir = tmp_path / "flows"
    with patch(
        "cherenkov.stages.mobile_cmd.MaestroRunner.health_check", return_value=True
    ), patch(
        "cherenkov.stages.mobile_cmd.MaestroRunner.run_test",
        return_value={"status": "passed", "executed": True, "stdout": "", "stderr": ""},
    ) as mock_run:
        result = CliRunner().invoke(
            mobile,
            [hil_file, "--app-id", "com.acme.shop", "--out", str(out_dir), "--json"],
        )
    assert result.exit_code == 0
    mock_run.assert_called_once()
    payload = json.loads(result.output)
    assert payload["executed"] == 1
    assert payload["flows"][0]["status"] == "passed"
    assert payload["flows"][0]["executed"] is True


def test_cli_fail_on_finding_exits_nonzero_on_device_failure(hil_file, tmp_path):
    with patch(
        "cherenkov.stages.mobile_cmd.MaestroRunner.health_check", return_value=True
    ), patch(
        "cherenkov.stages.mobile_cmd.MaestroRunner.run_test",
        return_value={"status": "failed", "executed": True, "stderr": "assert failed"},
    ):
        result = CliRunner().invoke(
            mobile,
            [
                hil_file,
                "--app-id",
                "com.acme.shop",
                "--out",
                str(tmp_path / "flows"),
                "--fail-on-finding",
            ],
        )
    assert result.exit_code == 1


def test_cli_does_not_send_gate_failures_to_the_device(hil_file, tmp_path):
    """A flow that fails review must not consume device time or report a run."""
    with patch(
        "cherenkov.stages.mobile_cmd.MaestroRunner.health_check", return_value=True
    ), patch(
        "cherenkov.stages.mobile_cmd.MaestroRunner.run_test"
    ) as mock_run, patch(
        "cherenkov.stages.mobile_cmd.MobileReviewStage.run",
        return_value=MagicMock(passed=False, errors=["weakened"], warnings=[]),
    ):
        result = CliRunner().invoke(
            mobile,
            [hil_file, "--out", str(tmp_path / "flows"), "--json"],
        )
    mock_run.assert_not_called()
    assert json.loads(result.output)["flows"][0]["status"] == "review_failed"


def test_cli_never_executes_demo_scenarios(tmp_path):
    with patch(
        "cherenkov.stages.mobile_cmd.MaestroRunner.health_check", return_value=True
    ), patch("cherenkov.stages.mobile_cmd.MaestroRunner.run_test") as mock_run:
        result = CliRunner().invoke(
            mobile, ["--demo", "--out", str(tmp_path / "demo"), "--json"]
        )
    mock_run.assert_not_called()
    payload = json.loads(result.output)
    assert payload["executed"] == 0
    assert any("not executed against a device" in n for n in payload["notes"])


def test_cli_rejects_har_source_with_actionable_message(tmp_path):
    har = tmp_path / "traffic.har"
    har.write_text(json.dumps({"log": {"entries": []}}), encoding="utf-8")
    result = CliRunner().invoke(mobile, [str(har), "--out", str(tmp_path / "flows")])
    assert result.exit_code != 0
    assert "records network traffic" in result.output


def test_cli_requires_a_source_or_demo():
    result = CliRunner().invoke(mobile, [])
    assert result.exit_code != 0
    assert "--demo" in result.output
