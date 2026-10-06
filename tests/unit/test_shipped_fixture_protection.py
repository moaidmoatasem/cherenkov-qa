"""Issue #994 — a default ``generate`` run deleted a tracked fixture (D7 violation).

``cherenkov generate`` with the default ``--output-dir`` (stub/generated_tests/)
ran a scenario whose mutation id is literally ``password_too_short``. The review
gates overwrote ``stub/generated_tests/password_too_short.spec.ts`` with the
candidate code, then generate_cmd's scratch cleanup removed that path — deleting
the committed catch-the-AI-cheating fixture.

These tests run against a temporary stub directory, never the real one.
"""
from __future__ import annotations

import os
import types

import pytest
from click.testing import CliRunner

from cherenkov.core.contracts import GateResult, GenerateOutput, StageMeta, Status
from cherenkov.execution.fixtures import is_shipped_fixture
from cherenkov.stages.review import ReviewStage

FIXTURE_ID = "password_too_short"
FIXTURE_BYTES = b"// tracked fixture - must never change\n"
CANDIDATE = "import { test } from '@playwright/test';\ntest('x', async () => {});\n"


def _gen(scenario_id: str) -> GenerateOutput:
    return GenerateOutput(
        scenario_id=scenario_id, test_code=CANDIDATE, endpoint="/users", method="POST",
        status=Status.OK, metadata=StageMeta(stage="GENERATE"),
    )


def _stage(monkeypatch, stub_dir, *, cleanup: bool, boom: bool = False) -> ReviewStage:
    """A ReviewStage whose subprocess-backed gates are stubbed out."""
    stage = ReviewStage(run_id="t994", cleanup_scratch=cleanup)
    stage.stub_dir = str(stub_dir)
    ok = GateResult(gate="stub", passed=True)
    seen = {}

    def tsc(self, scenario_id):
        # The candidate must really be on disk while the gates run.
        path = os.path.join(self.stub_dir, "generated_tests", f"{scenario_id}.spec.ts")
        with open(path, encoding="utf-8") as f:
            seen["during_gates"] = f.read()
        if boom:
            raise RuntimeError("gate crashed")
        return ok

    monkeypatch.setattr(ReviewStage, "_gate_tsc", tsc)
    monkeypatch.setattr(ReviewStage, "_gate_prism", lambda self, *a, **k: ok)
    for name in ("_gate_meaningful_assertion", "_gate_ocr", "_gate_consensus", "_log_finetune", "_bridge_hitl"):
        monkeypatch.setattr(ReviewStage, name, lambda self, *a, **k: None)
    stage.seen = seen
    return stage


@pytest.fixture
def stub_dir(tmp_path):
    (tmp_path / "generated_tests").mkdir()
    (tmp_path / "generated_tests" / f"{FIXTURE_ID}.spec.ts").write_bytes(FIXTURE_BYTES)
    return tmp_path


def test_shipped_fixture_names():
    assert is_shipped_fixture("password_too_short.spec.ts")
    assert is_shipped_fixture("/x/y/demo_weakened.spec.ts")
    assert is_shipped_fixture("golden_correct.spec.ts")
    assert not is_shipped_fixture("POST_users_password_too_short.spec.ts")
    assert not is_shipped_fixture("get_test_happy_path.spec.ts")


@pytest.mark.parametrize("cleanup", [False, True])
def test_review_restores_colliding_fixture(monkeypatch, stub_dir, cleanup):
    stage = _stage(monkeypatch, stub_dir, cleanup=cleanup)
    stage.run(_gen(FIXTURE_ID), spec_path="unused.yaml")
    assert stage.seen["during_gates"] == CANDIDATE
    assert (stub_dir / "generated_tests" / f"{FIXTURE_ID}.spec.ts").read_bytes() == FIXTURE_BYTES


def test_review_restores_fixture_even_when_a_gate_crashes(monkeypatch, stub_dir):
    stage = _stage(monkeypatch, stub_dir, cleanup=False, boom=True)
    with pytest.raises(RuntimeError):
        stage.run(_gen(FIXTURE_ID), spec_path="unused.yaml")
    assert (stub_dir / "generated_tests" / f"{FIXTURE_ID}.spec.ts").read_bytes() == FIXTURE_BYTES


def test_review_still_leaves_ordinary_scratch_file_by_default(monkeypatch, stub_dir):
    # The orchestrator relies on review's write being the artifact for
    # non-fixture scenarios; that behaviour must not change.
    stage = _stage(monkeypatch, stub_dir, cleanup=False)
    stage.run(_gen("post_users_happy_path"), spec_path="unused.yaml")
    assert (stub_dir / "generated_tests" / "post_users_happy_path.spec.ts").read_text() == CANDIDATE


def test_review_cleanup_removes_ordinary_scratch_file(monkeypatch, stub_dir):
    stage = _stage(monkeypatch, stub_dir, cleanup=True)
    stage.run(_gen("post_users_happy_path"), spec_path="unused.yaml")
    assert not (stub_dir / "generated_tests" / "post_users_happy_path.spec.ts").exists()


def test_generate_never_deletes_a_preexisting_file(monkeypatch, tmp_path, stub_dir):
    """The exact #994 path: default output dir == review scratch dir, scenario
    id == a tracked fixture name, RepairLoop on (the default)."""
    from cherenkov.cli.commands.generate_cmd import generate_cmd
    from cherenkov.core.contracts import Scenario

    out_dir = stub_dir / "generated_tests"
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text("openapi: '3.1.0'\ninfo: {title: T, version: '1'}\npaths: {}\n")
    scenario = Scenario(mutation_id=FIXTURE_ID, endpoint="/users", method="POST",
                        case_type="boundary", expected_status=400)
    endpoint = types.SimpleNamespace(path="/users", method="POST", operation={}, schemas={})
    monkeypatch.setattr("cherenkov.stages.ingest.IngestStage",
                        lambda run_id: types.SimpleNamespace(run=lambda spec: types.SimpleNamespace(endpoints=[endpoint])))
    monkeypatch.setattr("cherenkov.stages.plan.PlanStage",
                        lambda run_id: types.SimpleNamespace(run=lambda ing: types.SimpleNamespace(scenarios=[scenario])))
    monkeypatch.setattr("cherenkov.stages.review.default_review_scratch_dir", lambda: str(out_dir))
    monkeypatch.setattr("cherenkov.stages.repair.RepairLoop.__init__",
                        lambda self, run_id=None, max_attempts=3, cleanup_scratch=False: None)
    monkeypatch.setattr("cherenkov.stages.repair.RepairLoop.run", lambda self, **kw: (_gen(FIXTURE_ID), None))

    result = CliRunner().invoke(generate_cmd, ["--spec", str(spec_file), "--output-dir", str(out_dir)])

    assert result.exit_code == 0, result.output
    assert (out_dir / f"{FIXTURE_ID}.spec.ts").read_bytes() == FIXTURE_BYTES
    assert (out_dir / "POST_users_password_too_short.spec.ts").read_text() == CANDIDATE
