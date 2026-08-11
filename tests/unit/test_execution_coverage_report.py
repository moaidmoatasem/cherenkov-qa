"""Tests for cherenkov/execution/coverage_report.py — spec vs executed-test gaps."""

from __future__ import annotations

import json

import pytest

import cherenkov.core.config_loader as config_loader
import cherenkov.stages.ingest as ingest_module
from cherenkov.core.contracts import EndpointSlice, IngestOutput, StageMeta, Status
from cherenkov.execution.coverage_report import (
    _get_tested_scenarios,
    _load_spec_endpoints,
    generate_coverage_report,
)


def _endpoint(path: str, method: str, codes=("200", "404"), richness: float = 0.5) -> EndpointSlice:
    return EndpointSlice(
        path=path,
        method=method,
        operation={"responses": {c: {} for c in codes}},
        richness=richness,
    )


class FakeIngestStage:
    """Records construction args and returns a canned IngestOutput."""

    calls: list[str] = []
    endpoints: list[EndpointSlice] = []
    status: Status = Status.OK

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id

    def run(self, spec_path):
        """Placeholder docstring.

:param spec_path: <description>
:return: <description>"""
        type(self).calls.append(spec_path)
        return IngestOutput(
            endpoints=type(self).endpoints,
            client_stub_path="stub/client.ts",
            status=type(self).status,
            metadata=StageMeta(stage="ingest"),
        )


@pytest.fixture
    """Placeholder docstring.

:param monkeypatch: <description>
:return: <description>"""
def fake_ingest(monkeypatch):
    FakeIngestStage.calls = []
    FakeIngestStage.endpoints = []
    FakeIngestStage.status = Status.OK
    monkeypatch.setattr(ingest_module, "IngestStage", FakeIngestStage)
    return FakeIngestStage


# ── _load_spec_endpoints ───────────────────────────────────────────────────────
    """Placeholder docstring.

<description>"""
class TestLoadSpecEndpoints:
    def test_flattens_operations_with_numeric_response_codes(self, fake_ingest):
        """Placeholder docstring.

:param fake_ingest: <description>
:return: <description>"""
        fake_ingest.endpoints = [_endpoint("/pets", "GET", ("200", "404", "default"), 0.756)]
        assert _load_spec_endpoints("spec.json") == [
            {"path": "/pets", "method": "GET", "response_codes": ["200", "404"], "richness": 0.76}
        ]
        assert fake_ingest.calls == ["spec.json"]

    def test_failed_ingest_yields_no_endpoints(self, fake_ingest):
        """Placeholder docstring.

:param fake_ingest: <description>
:return: <description>"""
        fake_ingest.endpoints = [_endpoint("/pets", "GET")]
        fake_ingest.status = Status.FAILED
        assert _load_spec_endpoints("spec.json") == []

    def test_autodetects_the_spec_when_none_is_given(self, fake_ingest, monkeypatch):
        """Placeholder docstring.

:param fake_ingest: <description>
:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.setattr(
            config_loader.LayeredConfig,
            "autodetect_spec",
            lambda self: ["found.yaml", "other.yaml"],
        )
        fake_ingest.endpoints = [_endpoint("/pets", "GET")]
        assert _load_spec_endpoints(None)[0]["path"] == "/pets"
        assert fake_ingest.calls == ["found.yaml"]

    def test_no_spec_and_no_autodetection_yields_no_endpoints(self, monkeypatch):
        """Placeholder docstring.

:param monkeypatch: <description>
:return: <description>"""
        monkeypatch.setattr(config_loader.LayeredConfig, "autodetect_spec", lambda self: [])
        assert _load_spec_endpoints("") == []
    """Placeholder docstring.

<description>"""

# ── _get_tested_scenarios ──────────────────────────────────────────────────────


class TestGetTestedScenarios:
    def test_returns_spec_file_stems(self, tmp_path):
        """Placeholder docstring.

:param tmp_path: <description>
:return: <description>"""
        (tmp_path / "get_pets.spec.ts").write_text("", encoding="utf-8")
        (tmp_path / "post_pets.spec.ts").write_text("", encoding="utf-8")
        (tmp_path / "helper.ts").write_text("", encoding="utf-8")
        assert _get_tested_scenarios(str(tmp_path)) == {"get_pets", "post_pets"}

    def test_missing_directory_is_empty(self, tmp_path):
        """Placeholder docstring.

:param tmp_path: <description>
:return: <description>"""
    """Placeholder docstring.

<description>"""
        assert _get_tested_scenarios(str(tmp_path / "nope")) == set()


# ── generate_coverage_report ───────────────────────────────────────────────────


class TestGenerateCoverageReport:
    def test_matches_executed_scenarios_to_endpoints(self, fake_ingest, tmp_path, capsys):
        """Placeholder docstring.

:param fake_ingest: <description>
:param tmp_path: <description>
:param capsys: <description>
:return: <description>"""
        fake_ingest.endpoints = [
            _endpoint("/pets", "GET", ("200",)),
            _endpoint("/pets/{petId}", "DELETE", ("204", "404")),
        ]
        out_path = tmp_path / "out" / "coverage_report.json"
        report = generate_coverage_report(
            "spec.json",
            str(tmp_path / "tests"),
            executed_scenario_ids=["get_pets_happy"],
            out_path=str(out_path),
        )
        assert report["spec_endpoints"] == 2
        assert report["covered_endpoints"] == 1
        assert report["coverage_pct"] == 50.0
        assert report["uncovered"] == ["DELETE /pets/{petId}"]
        assert report["response_codes"] == {
            "in_spec": ["200", "204", "404"],
            "covered": ["200"],
            "missing": ["204", "404"],
        }
        assert json.loads(out_path.read_text(encoding="utf-8")) == report
        assert "Coverage Report" in capsys.readouterr().out

    def test_falls_back_to_generated_files_when_no_executions_given(self, fake_ingest, tmp_path):
        """Placeholder docstring.

:param fake_ingest: <description>
:param tmp_path: <description>
:return: <description>"""
        fake_ingest.endpoints = [_endpoint("/pets", "GET", ("200",))]
        tests_dir = tmp_path / "generated_tests"
        tests_dir.mkdir()
        (tests_dir / "get_pets.spec.ts").write_text("", encoding="utf-8")
        report = generate_coverage_report(
            "spec.json", str(tests_dir), out_path=str(tmp_path / "r.json")
        )
        assert report["tests_generated"] == 1
        assert report["covered_endpoints"] == 1

    def test_path_shaped_scenario_ids_also_match(self, fake_ingest, tmp_path):
        """Placeholder docstring.

:param fake_ingest: <description>
:param tmp_path: <description>
:return: <description>"""
        fake_ingest.endpoints = [_endpoint("/v1/pets", "GET", ("200",))]
        report = generate_coverage_report(
            "spec.json",
            str(tmp_path),
            executed_scenario_ids=["scenario_for_v1_pets"],
            out_path=str(tmp_path / "r.json"),
        )
        assert report["uncovered"] == []

    def test_empty_spec_reports_zero_coverage_without_dividing_by_zero(self, fake_ingest, tmp_path):
        """Placeholder docstring.

:param fake_ingest: <description>
:param tmp_path: <description>
:return: <description>"""
        report = generate_coverage_report(
            "spec.json", str(tmp_path), executed_scenario_ids=[], out_path=str(tmp_path / "r.json")
        )
        assert report["spec_endpoints"] == 0
        assert report["coverage_pct"] == 0.0
        assert report["response_codes"]["in_spec"] == []

    def test_uncovered_listing_is_truncated_in_the_summary(self, fake_ingest, tmp_path, capsys):
        """Placeholder docstring.

:param fake_ingest: <description>
:param tmp_path: <description>
:param capsys: <description>
:return: <description>"""
        fake_ingest.endpoints = [_endpoint(f"/p{i}", "GET", ("200",)) for i in range(12)]
        report = generate_coverage_report(
            "spec.json", str(tmp_path), executed_scenario_ids=[], out_path=str(tmp_path / "r.json")
        )
        out = capsys.readouterr().out
        assert len(report["uncovered"]) == 12
        assert "… and 2 more" in out

    def test_writes_the_report_relative_to_cwd(self, fake_ingest, tmp_path, monkeypatch):
        """Placeholder docstring.

:param fake_ingest: <description>
:param tmp_path: <description>
:param monkeypatch: <description>
:return: <description>"""
        fake_ingest.endpoints = [_endpoint("/pets", "GET", ("200",))]
        monkeypatch.chdir(tmp_path)
        generate_coverage_report("spec.json", "tests", out_path=".cherenkov/coverage_report.json")
        assert (tmp_path / ".cherenkov" / "coverage_report.json").is_file()
