"""tests/unit/test_generate_cmd.py — offline tests for the generate CLI command.

Verifies that generate_cmd routes correctly through RepairLoop (--repair) or
GenerateStage (--no-repair) without invoking the LLM, Ollama, or real file I/O.
"""
from __future__ import annotations

import types

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
        """Placeholder docstring.

:param monkeypatch: <description>
:param tmp_path: <description>
:return: <description>"""
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        calls = []

        def fake_gen_init(self, run_id=None):
            """Placeholder docstring.

:param run_id: <description>
:return: <description>"""
            self.run_id = run_id

        def fake_gen_run(self, **kwargs):
            """Placeholder docstring.

:param **kwargs: <description>
:return: <description>"""
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
        """Placeholder docstring.

:param monkeypatch: <description>
:param tmp_path: <description>
:return: <description>"""

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
        """Placeholder docstring.

:param monkeypatch: <description>
:param tmp_path: <description>
:return: <description>"""

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
        """Placeholder docstring.

:param monkeypatch: <description>
:param tmp_path: <description>
:return: <description>"""

    def test_repair_mode_calls_repair_loop(self, monkeypatch, tmp_path):
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        loop_calls = []

        def fake_loop_init(self, run_id=None, max_attempts=3, cleanup_scratch=False):
            """Placeholder docstring.

:param run_id: <description>
:param max_attempts: <description>
:param cleanup_scratch: <description>
:return: <description>"""
            self.run_id = run_id
            self.max_attempts = max_attempts

        def fake_loop_run(self, **kwargs):
            """Placeholder docstring.

:param **kwargs: <description>
:return: <description>"""
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

    def test_custom_output_dir_enables_scratch_cleanup(self, monkeypatch, tmp_path):
        """
        Regression: ReviewStage's tsc/Prism gates always write into
        stub/generated_tests/ regardless of --output-dir (that's the only
        path tsconfig.json/playwright.config.ts know about). generate_cmd
        must tell RepairLoop to clean that scratch copy up whenever the
        user's real --output-dir is something else, so a custom-output run
        doesn't leave stray files behind in the tracked fixture directory.
        """
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        captured = {}

        def fake_loop_init(self, run_id=None, max_attempts=3, cleanup_scratch=False):
            """Placeholder docstring.

:param run_id: <description>
:param max_attempts: <description>
:param cleanup_scratch: <description>
:return: <description>"""
            captured["cleanup_scratch"] = cleanup_scratch

        monkeypatch.setattr("cherenkov.stages.repair.RepairLoop.__init__", fake_loop_init)
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.run",
            lambda self, **kw: (_make_gen_output(), None),
        )

        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(tmp_path / "out")],
        )
        assert result.exit_code == 0, result.output
        assert captured.get("cleanup_scratch") is True

    def test_default_output_dir_disables_scratch_cleanup(self, monkeypatch, tmp_path):
        """When --output-dir resolves to the real stub/generated_tests/
        destination, RepairLoop must not be told to clean it up out from
        under the user."""
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        captured = {}

        def fake_loop_init(self, run_id=None, max_attempts=3, cleanup_scratch=False):
            """Placeholder docstring.

:param run_id: <description>
:param max_attempts: <description>
:param cleanup_scratch: <description>
:return: <description>"""
            captured["cleanup_scratch"] = cleanup_scratch

        monkeypatch.setattr("cherenkov.stages.repair.RepairLoop.__init__", fake_loop_init)
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.run",
            lambda self, **kw: (_make_gen_output(), None),
        )

        from cherenkov.stages.review import default_review_scratch_dir

        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", default_review_scratch_dir()],
        )
        assert result.exit_code == 0, result.output
        assert captured.get("cleanup_scratch") is False

    def test_repair_is_default(self, monkeypatch, tmp_path):
        """Running without any --repair/--no-repair flag should use repair mode."""
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        _loop_calls = []

        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.__init__",
            lambda self, run_id=None, max_attempts=3, cleanup_scratch=False: None,
        )
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.run",
            lambda self, **kw: (_make_gen_output(), None),
        )

        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
        """Placeholder docstring.

:param monkeypatch: <description>
:param tmp_path: <description>
:return: <description>"""
            ["--spec", str(spec_file), "--output-dir", str(tmp_path / "out")],
        )
        assert result.exit_code == 0
        assert "repair loop" in result.output

    def test_repair_writes_best_output(self, monkeypatch, tmp_path):
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)

        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.__init__",
            lambda self, run_id=None, max_attempts=3, cleanup_scratch=False: None,
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
        """Placeholder docstring.

:param monkeypatch: <description>
:param tmp_path: <description>
:return: <description>"""
        )
        assert result.exit_code == 0
        written = list(out_dir.glob("*.spec.ts"))
        assert len(written) == 1

    def test_max_attempts_forwarded_to_loop(self, monkeypatch, tmp_path):
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        captured = {}

        def fake_init(self, run_id=None, max_attempts=3, cleanup_scratch=False):
            """Placeholder docstring.

:param run_id: <description>
:param max_attempts: <description>
:param cleanup_scratch: <description>
:return: <description>"""
            captured["max_attempts"] = max_attempts

        monkeypatch.setattr("cherenkov.stages.repair.RepairLoop.__init__", fake_init)
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.run",
            lambda self, **kw: (_make_gen_output(), None),
        )

        runner = CliRunner()
        """Placeholder docstring.

:param monkeypatch: <description>
:param tmp_path: <description>
:return: <description>"""
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
            lambda self, run_id=None, max_attempts=3, cleanup_scratch=False: None,
        )
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.run",
            lambda self, **kw: (_make_gen_output(), _FakeReview()),
        )

        runner = CliRunner()
        result = runner.invoke(
        """Placeholder docstring.

:param monkeypatch: <description>
:param tmp_path: <description>
:return: <description>"""
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(tmp_path / "out")],
        )
        assert "auto_approve" in result.output
        assert "0.85" in result.output

    def test_no_review_output_when_review_is_none(self, monkeypatch, tmp_path):
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)

        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.__init__",
            lambda self, run_id=None, max_attempts=3, cleanup_scratch=False: None,
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
        """Placeholder docstring.

:return: <description>"""
class TestScenarioSpecFilename:
    """Regression (#828): mutation_id alone is not unique across scenarios
    (every endpoint contributes happy_path/unauthorized), so keying output
    filenames on it silently overwrote earlier scenarios — 38/38 reported
    "generated" while only 4 files persisted on disk."""

    def test_filename_includes_method_endpoint_and_mutation(self):
        from cherenkov.cli.commands.generate_cmd import scenario_spec_filename
        """Placeholder docstring.

:return: <description>"""

        assert (
            scenario_spec_filename("/pet", "POST", "happy_path")
            == "POST_pet_happy_path.spec.ts"
        )

    def test_duplicate_mutation_ids_produce_distinct_filenames(self):
        from cherenkov.cli.commands.generate_cmd import scenario_spec_filename
        """Placeholder docstring.

:return: <description>"""
        a = scenario_spec_filename("/pet", "POST", "happy_path")
        b = scenario_spec_filename("/pet", "PUT", "happy_path")
        assert a != b
        assert a == "POST_pet_happy_path.spec.ts"
        assert b == "PUT_pet_happy_path.spec.ts"

    def test_endpoint_special_chars_sanitized(self):
        from cherenkov.cli.commands.generate_cmd import scenario_spec_filename

        assert (
            scenario_spec_filename("/pet/{petId}", "GET", "happy_path")
            == "GET_pet_petId_happy_path.spec.ts"
        )
        assert (
            scenario_spec_filename("/store/order/{orderId}", "DELETE", "unauthorized")
            == "DELETE_store_order_orderId_unauthorized.spec.ts"
        )


class TestGenerateCmdFilenameCollision:
    """CLI-level regression (#828): scenarios sharing one mutation_id must
    each persist a distinct file instead of overwriting each other."""

    def _stub_multi_scenario_plan(self, monkeypatch, tmp_path, plan_scenarios):
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text("openapi: '3.0.4'\ninfo:\n  title: T\n  version: '1'\npaths: {}")

        class _FakeIngestOut:
            endpoints = [types.SimpleNamespace(
                path="/pet", method="POST",
                operation={"responses": {"200": {"description": "ok"}}},
                schemas={},
            )]

        class _FakePlanOut:
            scenarios = plan_scenarios

        monkeypatch.setattr(
            "cherenkov.stages.ingest.IngestStage",
            lambda run_id: types.SimpleNamespace(run=lambda spec: _FakeIngestOut()),
        )
        """Placeholder docstring.

:param monkeypatch: <description>
:param tmp_path: <description>
:return: <description>"""
        monkeypatch.setattr(
            "cherenkov.stages.plan.PlanStage",
            lambda run_id: types.SimpleNamespace(run=lambda ingest_out: _FakePlanOut()),
        )
        return spec_file

    def test_scenarios_sharing_mutation_id_persist_distinct_files(self, monkeypatch, tmp_path):
        from cherenkov.core.contracts import Scenario

        scenarios = [
            Scenario(mutation_id="happy_path", endpoint="/pet", method="POST",
                     case_type="happy_path", expected_status=201),
            Scenario(mutation_id="happy_path", endpoint="/pet", method="PUT",
                     case_type="happy_path", expected_status=200),
            Scenario(mutation_id="unauthorized", endpoint="/pet", method="POST",
                     case_type="auth", expected_status=401),
        ]
        spec_file = self._stub_multi_scenario_plan(monkeypatch, tmp_path, scenarios)

        monkeypatch.setattr(
            "cherenkov.stages.generate.GenerateStage.__init__",
            lambda self, run_id=None: None,
        )
        monkeypatch.setattr(
            "cherenkov.stages.generate.GenerateStage.run",
            lambda self, **kw: _make_gen_output(),
        )

        out_dir = tmp_path / "out"
        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(out_dir), "--no-repair"],
        )
        assert result.exit_code == 0, result.output
        assert "3/3" in result.output
        written = sorted(p.name for p in out_dir.glob("*.spec.ts"))
        assert written == [
            "POST_pet_happy_path.spec.ts",
            "POST_pet_unauthorized.spec.ts",
            "PUT_pet_happy_path.spec.ts",
        ]
        for name in written:
            assert _GOOD_CODE in (out_dir / name).read_text()

    def test_no_repair_never_removes_existing_files(self, monkeypatch, tmp_path):
        """D7-adjacent guard: --no-repair must never delete pre-existing files
        in the output directory (only the repair loop's own scratch copy is
        ever cleaned up, and only when writing to the scratch dir)."""
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        monkeypatch.setattr(
            "cherenkov.stages.generate.GenerateStage.__init__",
            lambda self, run_id=None: None,
        )
        monkeypatch.setattr(
            "cherenkov.stages.generate.GenerateStage.run",
            lambda self, **kw: _make_gen_output(),
        )

        out_dir = tmp_path / "out"
        unrelated = out_dir / "happy_path.spec.ts"
        out_dir.mkdir(parents=True, exist_ok=True)
        unrelated.write_text("user file", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(out_dir), "--no-repair"],
        )
        assert result.exit_code == 0
        assert unrelated.exists()

    def test_repair_mode_removes_collision_prone_scratch_copy(self, monkeypatch, tmp_path):
        """Regression (#828): the review gates leave a scratch copy at
        {mutation_id}.spec.ts inside the output dir. Once final files carry
        unique names, that stale collision-prone copy must be removed instead
        of lingering as a phantom fifth file."""
        spec_file, _ = _make_pipeline_stubs(monkeypatch, tmp_path)
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.__init__",
            lambda self, run_id=None, max_attempts=3, cleanup_scratch=False: None,
        )
        monkeypatch.setattr(
            "cherenkov.stages.repair.RepairLoop.run",
            lambda self, **kw: (_make_gen_output(), None),
        )
        monkeypatch.setattr(
            "cherenkov.stages.review.default_review_scratch_dir",
            lambda: str(tmp_path / "scratch"),
        )

        out_dir = tmp_path / "scratch"
        scratch = out_dir / "get_test_happy_path.spec.ts"
        out_dir.mkdir(parents=True, exist_ok=True)
        scratch.write_text("stale scratch from review gates", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            generate_cmd,
            ["--spec", str(spec_file), "--output-dir", str(out_dir), "--repair"],
        )
        assert result.exit_code == 0, result.output
        assert not scratch.exists(), "collision-prone scratch copy must be removed"
        written = sorted(p.name for p in out_dir.glob("*.spec.ts"))
        """Placeholder docstring.

:param monkeypatch: <description>
:param tmp_path: <description>
:return: <description>"""
        assert written == ["GET_test_get_test_happy_path.spec.ts"]


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
            lambda self, run_id=None, max_attempts=3, cleanup_scratch=False: None,
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
