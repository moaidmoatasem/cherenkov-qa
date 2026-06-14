"""
test_validate_gate.py
Unit tests for cherenkov/validate/ — contracts, gate logic, evidence collector.

D7 invariant: this file is created fresh, not auto-edited from existing tests.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from cherenkov.validate.contracts import GateCriteria, GateEvidence, ValidationReport
from cherenkov.validate.evidence import EvidenceCollector
from cherenkov.validate.gate import ValidationGate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_report(**kwargs) -> ValidationReport:
    defaults = dict(
        run_id="test-run-1",
        timestamp="2026-01-01T00:00:00+00:00",
        result="pass",
        gates=[],
        summary="result=PASS  gates=0/0 passed",
    )
    defaults.update(kwargs)
    return ValidationReport(**defaults)


def _make_subprocess_runner(returncode: int = 0, stdout: str = "ok", stderr: str = ""):
    """Return a callable that mimics subprocess.run with a fixed result."""

    def runner(*args, **kwargs):
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)

    return runner


# ---------------------------------------------------------------------------
# contracts.py tests
# ---------------------------------------------------------------------------


class TestValidationReport:
    def test_schema_version_default(self):
        report = _make_report()
        assert report.schema_version == "validate/v1"

    def test_round_trip_serialization(self):
        gate_ev = GateEvidence(gate="smoke_track_a", passed=True, detail="exit=0")
        report = _make_report(gates=[gate_ev])
        data = report.model_dump()
        restored = ValidationReport.model_validate(data)
        assert restored.schema_version == "validate/v1"
        assert restored.result == "pass"
        assert len(restored.gates) == 1
        assert restored.gates[0].gate == "smoke_track_a"

    def test_result_literal_pass(self):
        r = _make_report(result="pass")
        assert r.result == "pass"

    def test_result_literal_fail(self):
        r = _make_report(result="fail")
        assert r.result == "fail"

    def test_result_literal_degraded(self):
        r = _make_report(result="degraded")
        assert r.result == "degraded"

    def test_result_invalid_raises(self):
        with pytest.raises(Exception):
            _make_report(result="unknown")

    def test_evidence_dir_optional(self):
        r = _make_report()
        assert r.evidence_dir is None

    def test_evidence_dir_set(self):
        r = _make_report(evidence_dir="/tmp/ev")
        assert r.evidence_dir == "/tmp/ev"


class TestGateCriteria:
    def test_required_default_true(self):
        gc = GateCriteria(name="smoke_track_a", description="desc")
        assert gc.required is True

    def test_optional_gate(self):
        gc = GateCriteria(name="smoke_healing", description="optional", required=False)
        assert gc.required is False

    def test_model_round_trip(self):
        gc = GateCriteria(name="x", description="y", required=False)
        data = gc.model_dump()
        gc2 = GateCriteria.model_validate(data)
        assert gc2.name == "x"
        assert gc2.required is False


# ---------------------------------------------------------------------------
# gate.py tests
# ---------------------------------------------------------------------------


class TestValidationGateRun:
    def _make_gate(self, project_root: str | None = None) -> ValidationGate:
        return ValidationGate(project_root=project_root or "/fake/root")

    def test_all_pass_returns_pass(self):
        gate = self._make_gate()
        runner = _make_subprocess_runner(returncode=0)
        report = gate.run(_subprocess_runner=runner)
        assert report.result == "pass"
        assert report.schema_version == "validate/v1"

    def test_required_fail_returns_fail(self):
        gate = self._make_gate()
        call_count = [0]

        def runner(*args, **kwargs):
            call_count[0] += 1
            # fail the first script (smoke_track_a – required)
            rc = 1 if call_count[0] == 1 else 0
            return SimpleNamespace(
                returncode=rc, stdout="", stderr="fail" if rc else ""
            )

        report = gate.run(_subprocess_runner=runner)
        assert report.result == "fail"

    def test_optional_fail_returns_degraded(self):
        gate = self._make_gate()

        # Required gates: smoke_track_a, smoke_hitl_race, smoke_hitl_concurrency,
        #                 smoke_hitl_cli, smoke_eject, smoke_validate  (indices 0-5)
        # Optional gates: smoke_healing, smoke_polish (indices 6-7)
        call_count = [0]

        def runner(*args, **kwargs):
            call_count[0] += 1
            # fail only index 7 (smoke_polish, optional)
            rc = 1 if call_count[0] == 8 else 0
            return SimpleNamespace(returncode=rc, stdout="", stderr="")

        report = gate.run(_subprocess_runner=runner)
        assert report.result == "degraded"

    def test_run_id_auto_generated(self):
        gate = self._make_gate()
        runner = _make_subprocess_runner(returncode=0)
        report = gate.run(_subprocess_runner=runner)
        assert report.run_id  # non-empty

    def test_run_id_provided(self):
        gate = self._make_gate()
        runner = _make_subprocess_runner(returncode=0)
        report = gate.run(run_id="custom-123", _subprocess_runner=runner)
        assert report.run_id == "custom-123"

    def test_gate_names_in_report(self):
        gate = self._make_gate()
        runner = _make_subprocess_runner(returncode=0)
        report = gate.run(_subprocess_runner=runner)
        names = {g.gate for g in report.gates}
        assert "smoke_track_a" in names
        assert "smoke_healing" in names
        assert "smoke_eject" in names

    def test_evidence_dir_populated_in_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = self._make_gate()
            runner = _make_subprocess_runner(returncode=0)
            report = gate.run(_subprocess_runner=runner, evidence_dir=tmpdir)
            assert report.evidence_dir == tmpdir
            # files should exist
            files = list(Path(tmpdir).glob("*.txt"))
            assert len(files) == len(ValidationGate.GATE_CRITERIA)

    def test_summary_contains_result(self):
        gate = self._make_gate()
        runner = _make_subprocess_runner(returncode=0)
        report = gate.run(_subprocess_runner=runner)
        assert "PASS" in report.summary or "pass" in report.summary.lower()


# ---------------------------------------------------------------------------
# evidence.py tests
# ---------------------------------------------------------------------------


class TestEvidenceCollector:
    def test_record_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            col = EvidenceCollector(base_dir=tmpdir)
            path = col.record(
                "my_gate", passed=True, output="all good", detail="exit=0"
            )
            assert Path(path).exists()

    def test_record_content_contains_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            col = EvidenceCollector(base_dir=tmpdir)
            path = col.record("my_gate", passed=False, output="boom", detail="exit=1")
            content = Path(path).read_text()
            assert "STATUS: FAIL" in content
            assert "boom" in content

    def test_collect_all_returns_correct_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            col = EvidenceCollector(base_dir=tmpdir)
            col.record("gate_a", passed=True, output="ok")
            col.record("gate_b", passed=False, output="fail")
            items = col.collect_all()
            names = {i["name"] for i in items}
            assert "gate_a" in names
            assert "gate_b" in names
            assert len(items) == 2

    def test_collect_all_item_has_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            col = EvidenceCollector(base_dir=tmpdir)
            col.record("gate_x", passed=True, output="data")
            items = col.collect_all()
            assert items[0]["size"] > 0

    def test_summary_report_no_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            col = EvidenceCollector(base_dir=tmpdir)
            summary = col.summary_report()
            assert "No evidence" in summary

    def test_summary_report_with_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            col = EvidenceCollector(base_dir=tmpdir)
            col.record("gate_z", passed=True, output="output")
            summary = col.summary_report()
            assert "gate_z" in summary
            assert "Evidence summary" in summary

    def test_base_dir_created_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "a", "b", "c")
            col = EvidenceCollector(base_dir=nested)
            assert Path(nested).exists()
