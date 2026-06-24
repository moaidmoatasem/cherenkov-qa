"""tests/evals/test_repair_loop.py — offline tests for the ChatTester repair loop.

Verifies the RepairLoop contract without LLM, Docker, or network.
Uses monkeypatching to inject deterministic GenerateStage outputs.
"""
from __future__ import annotations

import pytest

from cherenkov.core.contracts import GenerateOutput, Scenario, StageMeta, Status
from cherenkov.core.errors import LoggerConfig
from cherenkov.stages.repair import RepairLoop, _extract_error_feedback

@pytest.fixture(autouse=True)
def _suppress_logging():
    LoggerConfig.suppress_stderr = True
    yield
    LoggerConfig.suppress_stderr = False

_SPEC_PATH = "stub/openapi_3_1.yaml"


def _make_scenario(mutation_id: str = "test_scenario") -> Scenario:
    return Scenario(
        mutation_id=mutation_id,
        endpoint="/test",
        method="GET",
        case_type="happy_path",
        expected_status=200,
    )


def _make_gen_output(code: str, scenario_id: str = "s1", ok: bool = True) -> GenerateOutput:
    return GenerateOutput(
        scenario_id=scenario_id,
        test_code=code,
        status=Status.OK if ok else Status.FAILED,
        metadata=StageMeta(stage="GENERATE"),
        endpoint="/test",
        method="GET",
    )


_GOOD_CODE = """\
import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /test happy_path', async () => {
  const { data, response } = await client.GET('/test', {});
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('id');
});
"""

_WEAK_CODE = """\
import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /test happy_path', async () => {
  const { data, response } = await client.GET('/test', {});
  expect(response.status).toBeLessThan(500);
});
"""


class _FakeGenerateStage:
    """Deterministic stand-in that returns a pre-set output sequence."""

    def __init__(self, outputs: list):
        self._outputs = list(outputs)
        self._idx = 0

    def run(self, **_kwargs):
        out = self._outputs[min(self._idx, len(self._outputs) - 1)]
        self._idx += 1
        return out


class TestRepairLoopContract:
    """Verify RepairLoop structure without real LLM calls."""

    def test_returns_tuple(self, monkeypatch):
        """RepairLoop.run() always returns (GenerateOutput, review_or_None)."""
        calls = []

        def fake_gen_init(self, run_id=None):
            self.run_id = run_id
            self.log = LoggerConfig  # stub

        def fake_gen_run(self, **kwargs):
            calls.append(kwargs.get("instruction", ""))
            return _make_gen_output(_GOOD_CODE)

        monkeypatch.setattr("cherenkov.stages.repair.GenerateStage.__init__", fake_gen_init)
        monkeypatch.setattr("cherenkov.stages.repair.GenerateStage.run", fake_gen_run)

        loop = RepairLoop(run_id="test-contract")
        gen_out, review = loop.run(
            scenario=_make_scenario(),
            path="/test",
            method="GET",
            spec_path=None,  # skip review
        )
        assert isinstance(gen_out, GenerateOutput)
        assert review is None

    def test_stops_without_spec_path(self, monkeypatch):
        """Without spec_path, loop runs exactly one generation and returns."""
        call_count = [0]

        def fake_gen_init(self, run_id=None):
            self.run_id = run_id

        def fake_gen_run(self, **kwargs):
            call_count[0] += 1
            return _make_gen_output(_GOOD_CODE)

        monkeypatch.setattr("cherenkov.stages.repair.GenerateStage.__init__", fake_gen_init)
        monkeypatch.setattr("cherenkov.stages.repair.GenerateStage.run", fake_gen_run)

        loop = RepairLoop(run_id="test-no-spec", max_attempts=3)
        loop.run(scenario=_make_scenario(), path="/test", method="GET", spec_path=None)
        assert call_count[0] == 1

    def test_failed_generation_returns_fallback(self, monkeypatch):
        """When generation fails, RepairLoop still returns a GenerateOutput."""

        def fake_gen_init(self, run_id=None):
            self.run_id = run_id

        def fake_gen_run(self, **kwargs):
            return _make_gen_output("", ok=False)

        monkeypatch.setattr("cherenkov.stages.repair.GenerateStage.__init__", fake_gen_init)
        monkeypatch.setattr("cherenkov.stages.repair.GenerateStage.run", fake_gen_run)

        loop = RepairLoop(run_id="test-failed", max_attempts=3)
        gen_out, _ = loop.run(scenario=_make_scenario(), spec_path=None)
        assert isinstance(gen_out, GenerateOutput)

    def test_repair_instruction_fed_on_second_attempt(self, monkeypatch):
        """On second attempt, instruction includes repair feedback."""
        received_instructions = []

        def fake_gen_init(self, run_id=None):
            self.run_id = run_id

        def fake_gen_run(self, **kwargs):
            received_instructions.append(kwargs.get("instruction", ""))
            return _make_gen_output(_WEAK_CODE)

        def fake_rev_init(self, run_id=None):
            self.run_id = run_id

        class _FakeReview:
            verdict = type("V", (), {"value": "hitl"})()
            quality_score = 0.5
            gates = [
                type("G", (), {"gate": "assertion", "passed": False, "skipped": False, "detail": "no specific status code"})()
            ]

        def fake_rev_run(self, gen_out, spec_path=None):
            return _FakeReview()

        monkeypatch.setattr("cherenkov.stages.repair.GenerateStage.__init__", fake_gen_init)
        monkeypatch.setattr("cherenkov.stages.repair.GenerateStage.run", fake_gen_run)
        monkeypatch.setattr("cherenkov.stages.repair.ReviewStage.__init__", fake_rev_init)
        monkeypatch.setattr("cherenkov.stages.repair.ReviewStage.run", fake_rev_run)

        loop = RepairLoop(run_id="test-repair-instr", max_attempts=2)
        loop.run(
            scenario=_make_scenario(),
            path="/test",
            method="GET",
            spec_path=_SPEC_PATH,
            instruction="original",
        )
        assert len(received_instructions) >= 2
        assert "REPAIR" in received_instructions[1]
        assert "assertion" in received_instructions[1]

    def test_best_score_returned(self, monkeypatch):
        """RepairLoop returns the attempt with the highest quality_score."""
        attempt_scores = [0.3, 0.8, 0.5]
        attempt_idx = [0]

        def fake_gen_init(self, run_id=None):
            self.run_id = run_id

        def fake_gen_run(self, **kwargs):
            return _make_gen_output(_WEAK_CODE)

        def fake_rev_init(self, run_id=None):
            self.run_id = run_id

        def fake_rev_run(self, gen_out, spec_path=None):
            score = attempt_scores[min(attempt_idx[0], len(attempt_scores) - 1)]
            attempt_idx[0] += 1

            class _R:
                verdict = type("V", (), {"value": "hitl"})()
                quality_score = score
                gates = [
                    type("G", (), {"gate": "assertion", "passed": False, "skipped": False, "detail": "weak"})()
                ]

            return _R()

        monkeypatch.setattr("cherenkov.stages.repair.GenerateStage.__init__", fake_gen_init)
        monkeypatch.setattr("cherenkov.stages.repair.GenerateStage.run", fake_gen_run)
        monkeypatch.setattr("cherenkov.stages.repair.ReviewStage.__init__", fake_rev_init)
        monkeypatch.setattr("cherenkov.stages.repair.ReviewStage.run", fake_rev_run)

        loop = RepairLoop(run_id="test-best-score", max_attempts=3)
        _, best_review = loop.run(
            scenario=_make_scenario(),
            path="/test",
            method="GET",
            spec_path=_SPEC_PATH,
        )
        assert best_review is not None
        assert best_review.quality_score == 0.8


class TestExtractErrorFeedback:
    """Unit tests for _extract_error_feedback helper."""

    def test_returns_empty_when_all_pass(self):
        class _G:
            gate = "syntax"
            passed = True
            skipped = False
            detail = ""

        class _Review:
            gates = [_G()]

        assert _extract_error_feedback(_Review()) == ""

    def test_returns_detail_from_first_failing_gate(self):
        class _G:
            gate = "assertion"
            passed = False
            skipped = False
            detail = "no .toBe() call found"

        class _Review:
            gates = [_G()]

        feedback = _extract_error_feedback(_Review())
        assert "assertion" in feedback
        assert "no .toBe() call found" in feedback

    def test_skipped_gates_ignored(self):
        class _Skip:
            gate = "tsc"
            passed = False
            skipped = True
            detail = "tsc not available"

        class _Review:
            gates = [_Skip()]

        assert _extract_error_feedback(_Review()) == ""

    def test_no_detail_still_returns_gate_name(self):
        class _G:
            gate = "structure"
            passed = False
            skipped = False
            detail = ""

        class _Review:
            gates = [_G()]

        feedback = _extract_error_feedback(_Review())
        assert "structure" in feedback
