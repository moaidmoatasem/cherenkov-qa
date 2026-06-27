"""tests/unit/test_generate_cmd.py — offline tests for the generate CLI command.

Verifies that generate_cmd routes correctly through RepairLoop (--repair) or
GenerateStage (--no-repair) without invoking the LLM, Ollama, or real file I/O.
"""
from __future__ import annotations

import types
from pathlib import Path

import pytest
from click.testing import CliRunner

from cherenkov.cli.commands.generate_cmd import generate_cmd
from cherenkov.core.contracts import GenerateOutput, StageMeta, Status
from cherenkov.core.errors import LoggerConfig


@pytest.fixture(autouse=True)
def _suppress_logging():
    LoggerConfig.suppress_stderr = True
    yield
    LoggerConfig.suppress_stderr = False


# ── shared stubs ──────────────────────────────────────────────────────────────

_SPEC_PATH = "stub/openapi_3_1.yaml"

_GOOD_CODE = """\
import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /test happy_path', async () => {
  const { data, response } = await client.GET('/test', {});
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('id');
});
"""


def _make_gen_output(code: str = _GOOD_CODE, ok: bool = True) -> GenerateOutput:
    return GenerateOutput(
        scenario_id="s1",
        test_code=code,
        status=Status.OK if ok else Status.FAILED,
        metadata=StageMeta(stage="GENERATE"),
        endpoint="/test",
        method="GET",
    )


def _make_pipeline_stubs(monkeypatch, tmp_path, spec_yaml: str = "openapi: '3.1.0'\ninfo:\n  title: T\n  version: '1'\npaths: {}"):
    """Patch IngestStage and PlanStage to return minimal fake outputs."""
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(spec_yaml)

    from cherenkov.core.contracts import Scenario

    fake_scenario = Scenario(
        mutation_id="get_test_happy_path",
        endpoint="/test",
        method="GET",
        case_type="happy_path",
        expected_status=200,
    )

    fake_endpoint = types.SimpleNamespace(
        path="/test",
        method="GET",
        operation={"responses": {"200": {"description": "ok"}}},
        schemas={},
    )

    class _FakeIngestOut:
        endpoints = [fake_endpoint]

    class _FakePlanOut:
        scenarios = [fake_scenario]

    # Patch at source module level — generate_cmd uses lazy imports inside the function
    monkeypatch.setattr(
        "cherenkov.stages.ingest.IngestStage",
        lambda run_id: types.SimpleNamespace(run=lambda spec: _FakeIngestOut()),
    )
    monkeypatch.setattr(
        "cherenkov.stages.plan.PlanStage",
        lambda run_id: types.SimpleNamespace(run=lambda ingest_out: _FakePlanOut()),
    )
    return spec_file, fake_scenario


# ── tests ─────────────────────────────────────────────────────────────────────

class TestGenerateCmdNoRepair:
    """--no-repair mode: single GenerateStage call, no RepairLoop."""

    def test_no_repair_calls_generate_stage(self, monkeypatch, tmp_path):
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        calls = []

        def fake_gen_init(self, run_id=None):
            self.run_id = run_id

        def fake_gen_run(self, **kwargs):
            calls.append(kwargs)
            return _make_gen_output()

        monkeypatch.setattr("cherenkov.stages.generate.GenerateStage.__init__", fake_gen_init)
        monkeypatch.setattr("cherenkov.stages.generate.GenerateStage.run", fake_gen_run)

        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(tmp_path / "out"), "--no-repair"],
        )
        assert result.exit_code == 0, result.output
        assert len(calls) == 1
        assert "Mode: single-pass" in result.output

    def test_no_repair_writes_test_file(self, monkeypatch, tmp_path):
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)

        monkeypatch.setattr("cherenkov.stages.generate.GenerateStage.__init__", lambda self, run_id=None: None)
        monkeypatch.setattr("cherenkov.stages.generate.GenerateStage.run", lambda self, **kw: _make_gen_output())

        out_dir = tmp_path / "out"
        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(out_dir), "--no-repair"],
        )
        assert result.exit_code == 0
        written = list(out_dir.glob("*.spec.ts"))
        assert len(written) == 1
        assert _GOOD_CODE in written[0].read_text()

    def test_no_repair_counts_successes(self, monkeypatch, tmp_path):
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        monkeypatch.setattr("cherenkov.stages.generate.GenerateStage.__init__", lambda self, run_id=None: None)
        monkeypatch.setattr("cherenkov.stages.generate.GenerateStage.run", lambda self, **kw: _make_gen_output())

        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(tmp_path / "out"), "--no-repair"],
        )
        assert "1/1" in result.output


class TestGenerateCmdWithRepair:
    """--repair mode (default): routes through RepairLoop."""

    def test_repair_mode_calls_repair_loop(self, monkeypatch, tmp_path):
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        loop_calls = []

        def fake_loop_init(self, run_id=None, max_attempts=3):
            self.run_id = run_id
            self.max_attempts = max_attempts

        def fake_loop_run(self, **kwargs):
            loop_calls.append(kwargs)
            return _make_gen_output(), None

        monkeypatch.setattr("cherenkov.stages.repair.RepairLoop.__init__", fake_loop_init)
        monkeypatch.setattr("cherenkov.stages.repair.RepairLoop.run", fake_loop_run)

        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(tmp_path / "out"), "--repair"],
        )
        assert result.exit_code == 0, result.output
        assert len(loop_calls) == 1
        assert "repair loop" in result.output

    def test_repair_is_default(self, monkeypatch, tmp_path):
        """Running without any --repair/--no-repair flag should use repair mode."""
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        loop_calls = []

        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.__init__",
            lambda self, run_id=None, max_attempts=3: None,
        )
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.run",
            lambda self, **kw: (_make_gen_output(), None),
        )

        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(tmp_path / "out")],
        )
        assert result.exit_code == 0
        assert "repair loop" in result.output

    def test_repair_writes_best_output(self, monkeypatch, tmp_path):
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)

        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.__init__",
            lambda self, run_id=None, max_attempts=3: None,
        )
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.run",
            lambda self, **kw: (_make_gen_output(), None),
        )

        out_dir = tmp_path / "out"
        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(out_dir)],
        )
        assert result.exit_code == 0
        written = list(out_dir.glob("*.spec.ts"))
        assert len(written) == 1

    def test_max_attempts_forwarded_to_loop(self, monkeypatch, tmp_path):
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        captured = {}

        def fake_init(self, run_id=None, max_attempts=3):
            captured["max_attempts"] = max_attempts

        monkeypatch.setattr("cherenkov.stages.repair.RepairLoop.__init__", fake_init)
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.run",
            lambda self, **kw: (_make_gen_output(), None),
        )

        runner = CliRunner()
        runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(tmp_path / "out"), "--max-attempts", "5"],
        )
        assert captured.get("max_attempts") == 5

    def test_review_verdict_printed_when_review_present(self, monkeypatch, tmp_path):
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)

        class _FakeReview:
            quality_score = 0.85
            verdict = types.SimpleNamespace(value="auto_approve")

        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.__init__",
            lambda self, run_id=None, max_attempts=3: None,
        )
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.run",
            lambda self, **kw: (_make_gen_output(), _FakeReview()),
        )

        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(tmp_path / "out")],
        )
        assert "auto_approve" in result.output
        assert "0.85" in result.output

    def test_no_review_output_when_review_is_none(self, monkeypatch, tmp_path):
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)

        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.__init__",
            lambda self, run_id=None, max_attempts=3: None,
        )
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.run",
            lambda self, **kw: (_make_gen_output(), None),
        )

        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(tmp_path / "out")],
        )
        assert "review:" not in result.output


class TestGenerateCmdErrorHandling:
    """Error cases in the generate command."""

    def test_ingest_failure_exits_1(self, monkeypatch, tmp_path):
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text("invalid")

        monkeypatch.setattr(
            "cherenkov.stages.ingest.IngestStage",
            lambda run_id: types.SimpleNamespace(run=lambda spec: (_ for _ in ()).throw(RuntimeError("bad spec"))),
        )

        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(tmp_path / "out")],
        )
        assert result.exit_code == 1
        assert "ERROR" in result.output

    def test_generation_error_continues_to_next_scenario(self, monkeypatch, tmp_path):
        """A single scenario failure should not abort the whole run."""
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)

        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.__init__",
            lambda self, run_id=None, max_attempts=3: None,
        )
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.run",
            lambda self, **kw: (_ for _ in ()).throw(RuntimeError("LLM down")),
        )

        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(tmp_path / "out")],
        )
        assert result.exit_code == 0
        assert "ERROR" in result.output
        assert "0/1" in result.output
