"""Tests for cherenkov/verdict/traffic_capture.py — TrafficCapture."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceHypothesis,
    ReproductionResult,
    Severity,
)
from cherenkov.verdict.traffic_capture import (
    CapturingWitnessAgent,
    CapturedInteraction,
    TrafficCapture,
    TrafficCaptureReport,
)


def _make_hypothesis() -> DivergenceHypothesis:
    return DivergenceHypothesis(
        id=str(uuid.uuid4()),
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a="spec says X",
        claim_b="impl does Y",
        predicted_evidence="signal",
        severity=Severity.LOW,
        endpoint="GET /test",
        repro_steps=["Send GET /test", "Expect 200"],
    )


def _make_evidence(status: str = "200", diff: str = "") -> DivergenceEvidence:
    return DivergenceEvidence(
        request_summary=f"GET http://test/test → {status} (10ms)",
        response_actual={"ok": True},
        response_expected={"ok": True},
        diff=diff,
    )


# ── CapturedInteraction ───────────────────────────────────────────────────────

class TestCapturedInteraction:
    def test_id_auto_generated(self):
        i = CapturedInteraction()
        assert i.id

    def test_to_fixture_roundtrip(self):
        i = CapturedInteraction(
            method="GET",
            url="http://test/pet",
            response_status=200,
            response_body={"id": 1},
            spec_conformant=True,
            hypothesis_id="abc",
        )
        fixture = i.to_fixture()
        assert fixture["method"] == "GET"
        assert fixture["spec_conformant"] is True
        assert "captured_at" in fixture


# ── CapturingWitnessAgent._record ─────────────────────────────────────────────

class TestCapturingWitnessAgent:
    def test_record_conformant_when_not_reproduced(self):
        agent = CapturingWitnessAgent.__new__(CapturingWitnessAgent)
        agent.base_url = "http://test"
        agent.interactions = []

        h = _make_hypothesis()
        ev = _make_evidence(diff="")
        result = ReproductionResult(
            hypothesis_id=h.id, reproduced=False, evidence=ev
        )
        agent._record(h, result)
        assert len(agent.interactions) == 1
        assert agent.interactions[0].spec_conformant is True

    def test_record_not_conformant_when_reproduced(self):
        agent = CapturingWitnessAgent.__new__(CapturingWitnessAgent)
        agent.base_url = "http://test"
        agent.interactions = []

        h = _make_hypothesis()
        ev = _make_evidence(diff="status mismatch: expected=400, actual=200")
        result = ReproductionResult(
            hypothesis_id=h.id, reproduced=True, evidence=ev
        )
        agent._record(h, result)
        assert agent.interactions[0].spec_conformant is False

    def test_record_no_evidence_skips(self):
        agent = CapturingWitnessAgent.__new__(CapturingWitnessAgent)
        agent.base_url = "http://test"
        agent.interactions = []

        h = _make_hypothesis()
        result = ReproductionResult(hypothesis_id=h.id, reproduced=False, evidence=None)
        agent._record(h, result)
        assert len(agent.interactions) == 0

    def test_dump_fixtures_writes_only_golden(self, tmp_path):
        agent = CapturingWitnessAgent.__new__(CapturingWitnessAgent)
        agent.base_url = "http://test"
        agent.interactions = [
            CapturedInteraction(spec_conformant=True),
            CapturedInteraction(spec_conformant=False),
            CapturedInteraction(spec_conformant=True),
        ]
        out = tmp_path / "fixtures.jsonl"
        count = agent.dump_fixtures(out)
        assert count == 2
        lines = out.read_text().strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            data = json.loads(line)
            assert data["spec_conformant"] is True


# ── TrafficCapture ─────────────────────────────────────────────────────────────

class TestTrafficCapture:
    def test_run_returns_report(self, tmp_path):
        capture = TrafficCapture.__new__(TrafficCapture)
        capture.base_url = "http://test"

        mock_agent = MagicMock(spec=CapturingWitnessAgent)
        mock_agent.interactions = [CapturedInteraction(spec_conformant=True)]
        mock_agent.dump_fixtures.return_value = 1
        capture.agent = mock_agent

        h = _make_hypothesis()
        report = capture.run([h], fixture_dir=tmp_path)
        assert isinstance(report, TrafficCaptureReport)

    def test_replay_loads_fixtures(self, tmp_path):
        fixture_file = tmp_path / "test.jsonl"
        records = [
            {"id": "1", "method": "GET", "url": "http://test", "spec_conformant": True},
            {"id": "2", "method": "POST", "url": "http://test/pet", "spec_conformant": True},
        ]
        with fixture_file.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        capture = TrafficCapture.__new__(TrafficCapture)
        loaded = capture.replay(fixture_file)
        assert len(loaded) == 2
        assert loaded[0]["id"] == "1"

    def test_replay_missing_file_returns_empty(self, tmp_path):
        capture = TrafficCapture.__new__(TrafficCapture)
        result = capture.replay(tmp_path / "nonexistent.jsonl")
        assert result == []

    def test_total_property(self):
        report = TrafficCaptureReport(
            interactions=[CapturedInteraction(), CapturedInteraction()],
            golden_count=1,
        )
        assert report.total == 2
