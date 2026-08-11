"""
tests/unit/test_mcp_tools_depth.py — unit tests for the #812 deepened MCP tool
surface: check_suite, verify, generate.

Each tool is the machine-facing twin of a `cherenkov` CLI command, reusing the
real pipeline code (check_suite static analysis, divergence proof_run, and the
Ingest→Plan→Generate/Repair stages respectively).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceReport,
    Severity,
    StageMeta,
)
from cherenkov.mcp import handlers
from cherenkov.mcp.handlers import TOOLS


def _call(name: str, args: dict) -> dict:
    """Call handle_tool_call with policy + guard bypassed (unit-test pattern)."""
    with patch.object(handlers._policy, "is_tool_allowed", return_value=True), patch(
        "cherenkov.mcp.handlers.get_guard"
    ) as mock_guard:
        mock_guard.return_value.check_tool_call.return_value = MagicMock(allowed=True)
        return handlers.handle_tool_call({"name": name, "arguments": args})


def _make_report(
    dc: DivergenceClass = DivergenceClass.D1_SPEC_CODE,
    sev: Severity = Severity.HIGH,
    endpoint: str = "POST /pet",
) -> DivergenceReport:
    ev = DivergenceEvidence(
        request_summary="POST https://example.com/pet → 500",
        diff="status mismatch: expected=400, actual=500",
        response_actual="500",
        response_expected="400",
    )
    return DivergenceReport(
        id="abc123",
        divergence_class=dc,
        claim_a="spec says 400",
        claim_b="impl returns 500",
        severity=sev,
        endpoint=endpoint,
        evidence=ev,
        repro_steps=["curl -X POST http://example.com/pet", "expect 400"],
        metadata=StageMeta(stage="proof_run"),
    )


# ── Registration ──────────────────────────────────────────────────────────────


class TestRegistration:
    """Placeholder docstring.

<description>"""
    def test_tools_registered(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        names = [t.name for t in TOOLS]
        assert "check_suite" in names
        assert "verify" in names
        assert "generate" in names

    def test_verify_requires_base_url(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        tool = next(t for t in TOOLS if t.name == "verify")
        assert "base_url" in tool.inputSchema.required

    def test_generate_requires_spec_path(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        tool = next(t for t in TOOLS if t.name == "generate")
        assert "spec_path" in tool.inputSchema.required

    def test_check_suite_descriptions_mention_cli_command(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        tool = next(t for t in TOOLS if t.name == "check_suite")
        assert "check-suite" in tool.description

    def test_tools_in_dispatch_table(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        for name in ("check_suite", "verify", "generate"):
            assert name in handlers._TOOL_DISPATCH


# ── check_suite ──────────────────────────────────────────────────────────────

_BASELINE_PY = '''
def test_get_user():
    resp = client.get("/users/1")
    body = resp.json()
    assert resp.status_code == 200
    assert body["id"] == 1
    assert body["name"] == "Alice"
'''

_CANDIDATE_WEAK_PY = '''
def test_get_user():
    resp = client.get("/users/1")
    body = resp.json()
    assert resp.status_code == 200
    assert body["id"] < 5
    assert body["name"] == "Alice"
'''

_SPEC_PY = """
openapi: 3.1.0
paths:
  /users/{id}:
    get:
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: integer
                  name:
                    type: string
"""

_BASELINE_TS = """
test('get user', async () => {
  const { data } = await client.GET('/users/1');
  expect(data.total).toBe(10);
});
"""

_CANDIDATE_WEAK_TS = """
test('get user', async () => {
  const { data } = await client.GET('/users/1');
  expect(data.total).toBeGreaterThan(5);
    """Placeholder docstring.

<description>"""
});
"""


class TestCheckSuite:
    def test_missing_candidate_returns_error(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        result = _call("check_suite", {})
        assert result.get("isError")

    def test_python_pass(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        result = _call(
            "check_suite",
            {
                "candidate_inline": _CANDIDATE_WEAK_PY,
                "baseline_inline": _CANDIDATE_WEAK_PY,
            },
        )
        report = json.loads(result["content"][0]["text"])
        assert report["verdict"] == "pass"
        assert report["language"] == "python"
        assert report["findings"] == []

    def test_python_weakened_assertion_detected(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        result = _call(
            "check_suite",
            {
                "candidate_inline": _CANDIDATE_WEAK_PY,
                "baseline_inline": _BASELINE_PY,
            },
        )
        report = json.loads(result["content"][0]["text"])
        assert report["verdict"] == "warn"
        assert report["summary"]["WEAKENED"] == 1
        assert any("WEAKENED" in f for f in report["findings"])

    def test_python_hallucinated_field_detected(self, tmp_path, monkeypatch) -> None:
        """Placeholder docstring.

:param tmp_path: <description>
:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.chdir(tmp_path)
        spec = tmp_path / "spec.yaml"
        spec.write_text(_SPEC_PY)
        result = _call(
            "check_suite",
            {
                "candidate_inline": "def test_x():\n    body = {'ghost': 1}\n    assert body['ghost'] == 1\n",
                "baseline_inline": "def test_x():\n    body = {'ghost': 1}\n    assert body['ghost'] == 1\n",
                "spec_path": str(spec),
            },
        )
        report = json.loads(result["content"][0]["text"])
        assert report["summary"]["HALLUCINATED"] == 1

    def test_typescript_weakened_detected(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        result = _call(
            "check_suite",
            {
                "candidate_inline": _CANDIDATE_WEAK_TS,
                "baseline_inline": _BASELINE_TS,
            },
        )
        report = json.loads(result["content"][0]["text"])
        assert report["language"] == "typescript"
        assert report["summary"]["WEAKENED"] == 1

    def test_fail_on_finding_flips_verdict(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        result = _call(
            "check_suite",
            {
                "candidate_inline": _CANDIDATE_WEAK_PY,
                "baseline_inline": _BASELINE_PY,
                "fail_on_finding": True,
            },
        )
        report = json.loads(result["content"][0]["text"])
        assert report["verdict"] == "fail"

    def test_candidate_path_read_from_disk(self, tmp_path, monkeypatch) -> None:
        """Placeholder docstring.

:param tmp_path: <description>
:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.chdir(tmp_path)
        candidate = tmp_path / "candidate.py"
        candidate.write_text(_BASELINE_PY)
        result = _call("check_suite", {"candidate_path": str(candidate)})
        report = json.loads(result["content"][0]["text"])
        assert report["verdict"] == "pass"
        assert report["candidate"] == str(candidate)

    def test_path_outside_cwd_rejected(self, tmp_path, monkeypatch) -> None:
        """Placeholder docstring.

:param tmp_path: <description>
:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.chdir(tmp_path)
        outside = tmp_path / ".." / "outside_812.py"
        outside.parent.mkdir(exist_ok=True)
        outside.write_text(_BASELINE_PY)
    """Placeholder docstring.

<description>"""
        result = _call("check_suite", {"candidate_path": str(outside.resolve())})
        assert result.get("isError")

    def test_missing_file_returns_error(self, tmp_path, monkeypatch) -> None:
        """Placeholder docstring.

:param tmp_path: <description>
:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.chdir(tmp_path)
        result = _call("check_suite", {"candidate_path": "nope.py"})
        assert result.get("isError")


# ── verify ───────────────────────────────────────────────────────────────────


class TestVerify:
    def test_missing_base_url_returns_error(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        result = _call("verify", {})
        assert result.get("isError")

    def test_no_divergences_returns_pass(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[]):
            result = _call("verify", {"base_url": "http://localhost:9999"})
        report = json.loads(result["content"][0]["text"])
        assert report["verdict"] == "pass"
        assert report["summary"]["total"] == 0
        assert report["schema_version"] == "verify/v1"

    def test_divergences_returned_as_fail(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[_make_report()]):
            result = _call("verify", {"base_url": "http://localhost:9999"})
        report = json.loads(result["content"][0]["text"])
        assert report["verdict"] == "fail"
        assert report["summary"]["total"] == 1
        assert report["summary"]["high"] == 1

    def test_max_probes_passed_through(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[]) as mock:
            _call("verify", {"base_url": "http://localhost:9999", "max_probes": 7})
        _, kwargs = mock.call_args
        assert kwargs.get("max_probes") == 7

    def test_use_llm_and_allow_mutations_passed_through(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[]) as mock:
            _call(
                "verify",
                {
                    "base_url": "http://localhost:9999",
                    "use_llm": True,
                    "allow_mutations": True,
                },
            )
        _, kwargs = mock.call_args
        assert kwargs.get("use_llm") is True
        assert kwargs.get("allow_mutations") is True

    def test_identifiers_inline_json(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[]) as mock:
            _call(
                "verify",
                {
                    "base_url": "http://localhost:9999",
                    "identifiers": '{"petId": ["1", "2"]}',
                },
            )
        _, kwargs = mock.call_args
        assert kwargs.get("known_identifiers") == {"petId": ["1", "2"]}

    def test_coverage_report_section(self, tmp_path, monkeypatch) -> None:
        """Placeholder docstring.

:param tmp_path: <description>
:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.chdir(tmp_path)
        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps({"paths": {"/pet": {"get": {}}}}))
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[]):
            result = _call(
                "verify",
                {
                    "base_url": "http://localhost:9999",
                    "spec_source": str(spec),
                    "coverage_report": True,
                },
            )
        report = json.loads(result["content"][0]["text"])
        assert "coverage" in report
        assert report["coverage"]["total_endpoints"] == 1
        assert report["coverage"]["untested_count"] == 1

    def test_health_score_section(self, tmp_path, monkeypatch) -> None:
        """Placeholder docstring.

:param tmp_path: <description>
:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.chdir(tmp_path)
        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps({"paths": {"/pet": {"get": {}}}}))
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[]):
            result = _call(
                "verify",
                {
                    "base_url": "http://localhost:9999",
                    "spec_source": str(spec),
                    "health_score": True,
                },
            )
        report = json.loads(result["content"][0]["text"])
        assert "health" in report
        assert "grade" in report["health"]

    def test_engine_error_returns_error_result(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        with patch(
            "cherenkov.mcp.handlers.run_proof", side_effect=RuntimeError("boom")
        ):
            result = _call("verify", {"base_url": "http://localhost:9999"})
        assert result.get("isError")
        assert "boom" in result["content"][0]["text"]


# ── generate ─────────────────────────────────────────────────────────────────


def _fake_scenario() -> SimpleNamespace:
    return SimpleNamespace(
        endpoint="/users",
        method="GET",
        case_type="happy",
        mutation_id="user_happy",
        expected_status=200,
        instruction="",
    )


def _fake_ingest_out() -> SimpleNamespace:
    """Placeholder docstring.

<description>"""
    ep = SimpleNamespace(
        path="/users", method="GET", operation={}, schemas={}
    )
    return SimpleNamespace(endpoints=[ep])


def _fake_plan_out() -> SimpleNamespace:
    return SimpleNamespace(scenarios=[_fake_scenario()])


def _fake_gen_out() -> SimpleNamespace:
    return SimpleNamespace(
        test_code="test('user', async () => { await client.GET('/users'); });"
    )


def _fake_review() -> SimpleNamespace:
    return SimpleNamespace(
        verdict=SimpleNamespace(value="auto_approve"), quality_score=0.95
    )


class TestGenerate:
    def test_missing_spec_path_returns_error(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        result = _call("generate", {})
        assert result.get("isError")

    def test_spec_outside_cwd_rejected(self, tmp_path, monkeypatch) -> None:
        """Placeholder docstring.

:param tmp_path: <description>
:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.chdir(tmp_path)
        outside = tmp_path / ".." / "outside_spec.json"
        outside.parent.mkdir(exist_ok=True)
        outside.write_text("{}")
        result = _call("generate", {"spec_path": str(outside.resolve())})
        assert result.get("isError")

    def test_inline_return_by_default(self, tmp_path, monkeypatch) -> None:
        """Placeholder docstring.

:param tmp_path: <description>
:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.chdir(tmp_path)
        spec = tmp_path / "spec.json"
        spec.write_text("{}")
        with patch("cherenkov.stages.ingest.IngestStage") as Ingest, patch(
            "cherenkov.stages.plan.PlanStage"
        ) as Plan, patch("cherenkov.stages.repair.RepairLoop") as Repair:
            Ingest.return_value.run.return_value = _fake_ingest_out()
            Plan.return_value.run.return_value = _fake_plan_out()
            Repair.return_value.run.return_value = (_fake_gen_out(), _fake_review())
            result = _call("generate", {"spec_path": str(spec)})
        payload = json.loads(result["content"][0]["text"])
        assert payload["generated"] == 1
        assert payload["success_count"] == 1
        assert payload["output_dir"] is None
        scenario = payload["scenarios"][0]
        assert scenario["test_code"].startswith("test(")
        assert scenario["verdict"] == "auto_approve"
        assert scenario["quality_score"] == 0.95

    def test_output_dir_writes_files(self, tmp_path, monkeypatch) -> None:
        """Placeholder docstring.

:param tmp_path: <description>
:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.chdir(tmp_path)
        spec = tmp_path / "spec.json"
        spec.write_text("{}")
        out_dir = tmp_path / "generated"
        with patch("cherenkov.stages.ingest.IngestStage") as Ingest, patch(
            "cherenkov.stages.plan.PlanStage"
        ) as Plan, patch("cherenkov.stages.repair.RepairLoop") as Repair:
            Ingest.return_value.run.return_value = _fake_ingest_out()
            Plan.return_value.run.return_value = _fake_plan_out()
            Repair.return_value.run.return_value = (_fake_gen_out(), _fake_review())
            result = _call(
                "generate", {"spec_path": str(spec), "output_dir": str(out_dir)}
            )
        payload = json.loads(result["content"][0]["text"])
        scenario = payload["scenarios"][0]
        assert "test_code" not in scenario
        assert "file_path" in scenario
        written = out_dir / "user_happy.spec.ts"
        assert written.read_text(encoding="utf-8").startswith("test(")
        assert payload["output_dir"] == str(out_dir)

    def test_no_repair_uses_generate_stage(self, tmp_path, monkeypatch) -> None:
        """Placeholder docstring.

:param tmp_path: <description>
:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.chdir(tmp_path)
        spec = tmp_path / "spec.json"
        spec.write_text("{}")
        with patch("cherenkov.stages.ingest.IngestStage") as Ingest, patch(
            "cherenkov.stages.plan.PlanStage"
        ) as Plan, patch("cherenkov.stages.generate.GenerateStage") as Gen:
            Ingest.return_value.run.return_value = _fake_ingest_out()
            Plan.return_value.run.return_value = _fake_plan_out()
            Gen.return_value.run.return_value = _fake_gen_out()
            result = _call("generate", {"spec_path": str(spec), "repair": False})
        payload = json.loads(result["content"][0]["text"])
        assert payload["success_count"] == 1
        Gen.return_value.run.assert_called_once()

    def test_scenario_failure_is_recorded_not_fatal(self, tmp_path, monkeypatch) -> None:
        """Placeholder docstring.

:param tmp_path: <description>
:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.chdir(tmp_path)
        spec = tmp_path / "spec.json"
        spec.write_text("{}")
        with patch("cherenkov.stages.ingest.IngestStage") as Ingest, patch(
            "cherenkov.stages.plan.PlanStage"
        ) as Plan, patch(
            "cherenkov.stages.repair.RepairLoop",
            side_effect=RuntimeError("LLM backend unavailable"),
        ):
            Ingest.return_value.run.return_value = _fake_ingest_out()
            Plan.return_value.run.return_value = _fake_plan_out()
            result = _call("generate", {"spec_path": str(spec)})
        payload = json.loads(result["content"][0]["text"])
        assert payload["generated"] == 1
        assert payload["success_count"] == 0
        assert "LLM backend unavailable" in payload["scenarios"][0]["error"]
