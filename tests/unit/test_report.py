"""Unit tests for cherenkov/divergence/report_diff.py and cherenkov/cli/commands/report.py."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cherenkov.divergence.report_diff import ReportDiff, diff_reports, _stable_key


# ── fixtures ───────────────────────────────────────────────────────────────────

def _div(endpoint: str, claim_a: str = "spec says 400", sev: str = "HIGH") -> dict:
    return {
        "endpoint": endpoint,
        "divergence_class": "D1_SPEC_CODE",
        "claim_a": claim_a,
        "claim_b": "impl returns 500",
        "severity": sev,
    }


_D1 = _div("GET /pets", "spec says 200")
_D2 = _div("POST /pets", "spec says 201")
_D3 = _div("DELETE /pets/{id}", "spec says 204", "MEDIUM")


# ── TestStableKey ──────────────────────────────────────────────────────────────

class TestStableKey:
    def test_same_divergence_same_key(self):
        assert _stable_key(_D1) == _stable_key(_D1)

    def test_different_endpoints_different_keys(self):
        assert _stable_key(_D1) != _stable_key(_D2)

    def test_claim_a_truncated_to_80(self):
        long = _div("GET /x", "a" * 200)
        short = _div("GET /x", "a" * 200)
        assert _stable_key(long) == _stable_key(short)

    def test_missing_fields_handled(self):
        k = _stable_key({})
        assert isinstance(k, str)


# ── TestDiffReports ────────────────────────────────────────────────────────────

class TestDiffReports:
    def test_all_new_when_empty_baseline(self):
        diff = diff_reports([], [_D1, _D2])
        assert len(diff.new) == 2
        assert len(diff.resolved) == 0
        assert len(diff.unchanged) == 0

    def test_all_resolved_when_empty_current(self):
        diff = diff_reports([_D1, _D2], [])
        assert len(diff.new) == 0
        assert len(diff.resolved) == 2

    def test_all_unchanged_when_identical(self):
        diff = diff_reports([_D1, _D2], [_D1, _D2])
        assert len(diff.new) == 0
        assert len(diff.resolved) == 0
        assert len(diff.unchanged) == 2

    def test_mixed_new_resolved_unchanged(self):
        baseline = [_D1, _D2]
        current = [_D1, _D3]  # _D2 resolved, _D3 new
        diff = diff_reports(baseline, current)
        assert len(diff.new) == 1
        assert diff.new[0]["endpoint"] == "DELETE /pets/{id}"
        assert len(diff.resolved) == 1
        assert diff.resolved[0]["endpoint"] == "POST /pets"
        assert len(diff.unchanged) == 1

    def test_has_new_false_when_no_new(self):
        diff = diff_reports([_D1], [_D1])
        assert diff.has_new is False

    def test_has_new_true_when_new_found(self):
        diff = diff_reports([], [_D1])
        assert diff.has_new is True

    def test_summary_line_all_new(self):
        diff = diff_reports([], [_D1, _D2])
        assert "+2 new" in diff.summary_line

    def test_summary_line_mixed(self):
        diff = diff_reports([_D1, _D2], [_D1, _D3])
        assert "+1 new" in diff.summary_line
        assert "-1 resolved" in diff.summary_line
        assert "1 unchanged" in diff.summary_line

    def test_summary_line_no_change(self):
        diff = diff_reports([], [])
        assert diff.summary_line == "no change"

    def test_empty_both(self):
        diff = diff_reports([], [])
        assert diff.new == []
        assert diff.resolved == []
        assert diff.unchanged == []


# ── TestReportCmd (CLI) ────────────────────────────────────────────────────────

class TestReportCmd:
    def _invoke(self, args, files: dict[str, list] | None = None):
        from cherenkov.cli.commands.report import report_cmd
        runner = CliRunner()
        with runner.isolated_filesystem():
            if files:
                for name, data in files.items():
                    Path(name).write_text(json.dumps(data))
            return runner.invoke(report_cmd, args)

    def test_help(self):
        from cherenkov.cli.commands.report import report_cmd
        runner = CliRunner()
        result = runner.invoke(report_cmd, ["--help"])
        assert result.exit_code == 0
        assert "--diff" in result.output

    def test_text_summary(self):
        result = self._invoke(["report.json"], {"report.json": [_D1, _D2]})
        assert result.exit_code == 0
        assert "CHERENKOV Report" in result.output
        assert "GET /pets" in result.output

    def test_json_format(self):
        result = self._invoke(["report.json", "--format", "json"], {"report.json": [_D1]})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total"] == 1
        assert data["divergences"][0]["endpoint"] == "GET /pets"

    def test_markdown_format(self):
        result = self._invoke(["report.json", "--format", "markdown"], {"report.json": [_D1]})
        assert result.exit_code == 0
        assert "# CHERENKOV Report" in result.output
        assert "| 1 |" in result.output

    def test_output_writes_file(self, tmp_path):
        from cherenkov.cli.commands.report import report_cmd
        runner = CliRunner()
        report_file = tmp_path / "input.json"
        report_file.write_text(json.dumps([_D1, _D2]))
        out = tmp_path / "out.txt"
        result = runner.invoke(report_cmd, [str(report_file), "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert "GET /pets" in out.read_text()

    def test_diff_text(self):
        result = self._invoke(
            ["current.json", "--diff", "baseline.json"],
            {"baseline.json": [_D1, _D2], "current.json": [_D1, _D3]},
        )
        assert result.exit_code == 0
        assert "NEW" in result.output
        assert "RESOLVED" in result.output
        assert "UNCHANGED" in result.output

    def test_diff_json_format(self):
        result = self._invoke(
            ["current.json", "--diff", "baseline.json", "--format", "json"],
            {"baseline.json": [_D1], "current.json": [_D1, _D2]},
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["new_count"] == 1
        assert data["resolved_count"] == 0
        assert data["unchanged_count"] == 1

    def test_diff_markdown_format(self):
        result = self._invoke(
            ["current.json", "--diff", "baseline.json", "--format", "markdown"],
            {"baseline.json": [_D1], "current.json": [_D1, _D2]},
        )
        assert result.exit_code == 0
        assert "## New" in result.output

    def test_fail_on_new_exits_1_when_new_found(self):
        result = self._invoke(
            ["current.json", "--diff", "baseline.json", "--fail-on-new"],
            {"baseline.json": [_D1], "current.json": [_D1, _D2]},
        )
        assert result.exit_code == 1

    def test_fail_on_new_exits_0_when_no_new(self):
        result = self._invoke(
            ["current.json", "--diff", "baseline.json", "--fail-on-new"],
            {"baseline.json": [_D1, _D2], "current.json": [_D1]},
        )
        assert result.exit_code == 0

    def test_fail_on_new_without_diff_exits_0(self):
        result = self._invoke(["report.json", "--fail-on-new"], {"report.json": [_D1]})
        assert result.exit_code == 0

    def test_cert_json_accepted(self):
        """Divergence JSON wrapped in a certificate envelope is handled."""
        cert_data = {"divergences_json": [_D1, _D2], "verdict": "FAIL"}
        result = self._invoke(["cert.json"], {"cert.json": cert_data})
        assert result.exit_code == 0
        assert "GET /pets" in result.output

    def test_empty_report_shows_zero(self):
        result = self._invoke(["empty.json"], {"empty.json": []})
        assert result.exit_code == 0
        assert "0 divergence" in result.output

    def test_invalid_json_exits_2(self, tmp_path):
        from cherenkov.cli.commands.report import report_cmd
        runner = CliRunner()
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        result = runner.invoke(report_cmd, [str(bad)])
        assert result.exit_code == 2


# ── TestReportCmdStoreMode ─────────────────────────────────────────────────────

def _make_record(
    run_id: str = "aaaa-bbbb",
    verdict: str = "CERTIFIED",
    divergence_count: int = 2,
    coverage_pct: float | None = 87.5,
    duration_ms: int = 450,
    target_url: str = "http://petstore.example.com",
    timestamp: str = "2026-06-29T10:00:00Z",
    grade: str | None = "B",
    overall: str | None = "CERTIFIED",
):
    record = MagicMock()
    record.run_id = run_id
    record.command = "verify"
    record.verdict = verdict
    record.divergence_count = divergence_count
    record.coverage_pct = coverage_pct
    record.duration_ms = duration_ms
    record.target_url = target_url
    record.timestamp = timestamp

    rv: dict = {}
    if grade:
        rv = {
            "grade": grade,
            "overall": overall,
            "confidence": 0.82,
            "risk_flags": ["LOW_COVERAGE"],
            "top_findings": [
                {
                    "rank": 1,
                    "severity": "high",
                    "endpoint": "GET /pets",
                    "summary": "enum not enforced",
                    "remediation": "add enum validation",
                    "estimated_fix_minutes": 30,
                }
            ],
            "dimensions": [
                {"name": "divergence_probe", "score": 0.82, "grade": "B", "passed": True},
                {"name": "spec_coverage", "score": 0.95, "grade": "A", "passed": True},
            ],
            "time_to_fix_estimate": "~30min",
        }
    record.meta_json = json.dumps({"rich_verdict": rv} if rv else {})
    return record


def _mock_store(records: list, diff_result: dict | None = None):
    store = MagicMock()
    store.list.return_value = records
    store.get.side_effect = lambda run_id: next((r for r in records if r.run_id == run_id), None)
    if diff_result is not None:
        store.diff.return_value = diff_result
    return store


class TestReportCmdStoreMode:
    def _run(self, args: list[str], records=None, diff_result=None):
        from cherenkov.cli.commands.report import report_cmd
        recs = records if records is not None else [_make_record()]
        store = _mock_store(recs, diff_result)
        runner = CliRunner()
        with patch("cherenkov.cli.commands.report.get_run_store", return_value=store), \
             patch("cherenkov.persistence.run_store.get_run_store", return_value=store):
            # patch inside report module's lazy imports
            with patch("cherenkov.cli.commands.report._resolve_run") as mock_resolve:
                if args and args[0] not in ("--list", "--run", "--format", "--output", "--fail-on-new"):
                    pass  # file mode — don't patch resolve_run
                mock_resolve.side_effect = lambda rid: (
                    recs[0] if rid == "latest" else next((r for r in recs if r.run_id == rid), None)
                )
                return runner.invoke(report_cmd, args)

    def test_default_no_args_shows_latest_run(self):
        from cherenkov.cli.commands.report import report_cmd, _resolve_run
        record = _make_record()
        runner = CliRunner()
        with patch("cherenkov.cli.commands.report._resolve_run", return_value=record):
            result = runner.invoke(report_cmd, [])
        assert result.exit_code == 0
        assert "CHERENKOV Run" in result.output
        assert "aaaa-bbbb" in result.output

    def test_run_latest_text(self):
        from cherenkov.cli.commands.report import report_cmd
        record = _make_record()
        runner = CliRunner()
        with patch("cherenkov.cli.commands.report._resolve_run", return_value=record):
            result = runner.invoke(report_cmd, ["--run", "latest"])
        assert result.exit_code == 0
        assert "Grade: B" in result.output
        assert "CERTIFIED" in result.output

    def test_run_json_format(self):
        from cherenkov.cli.commands.report import report_cmd
        record = _make_record()
        runner = CliRunner()
        with patch("cherenkov.cli.commands.report._resolve_run", return_value=record):
            result = runner.invoke(report_cmd, ["--run", "latest", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["run_id"] == "aaaa-bbbb"
        assert data["grade"] == "B"
        assert data["verdict"] == "CERTIFIED"
        assert len(data["dimensions"]) == 2

    def test_run_markdown_format(self):
        from cherenkov.cli.commands.report import report_cmd
        record = _make_record()
        runner = CliRunner()
        with patch("cherenkov.cli.commands.report._resolve_run", return_value=record):
            result = runner.invoke(report_cmd, ["--run", "latest", "--format", "markdown"])
        assert result.exit_code == 0
        assert "## Grade: B" in result.output
        assert "## Dimensions" in result.output
        assert "## Risk Flags" in result.output

    def test_run_not_found_exits_2(self):
        from cherenkov.cli.commands.report import report_cmd
        runner = CliRunner()
        with patch("cherenkov.cli.commands.report._resolve_run", return_value=None):
            result = runner.invoke(report_cmd, ["--run", "missing-id"])
        assert result.exit_code == 2

    def test_run_no_rich_verdict_still_renders(self):
        from cherenkov.cli.commands.report import report_cmd
        record = _make_record(grade=None)
        runner = CliRunner()
        with patch("cherenkov.cli.commands.report._resolve_run", return_value=record):
            result = runner.invoke(report_cmd, ["--run", "latest"])
        assert result.exit_code == 0
        assert "aaaa-bbbb" in result.output

    def test_list_text(self):
        from cherenkov.cli.commands.report import report_cmd
        records = [_make_record(run_id=f"run-{i}", verdict="PASS") for i in range(3)]
        store = _mock_store(records)
        runner = CliRunner()
        with patch("cherenkov.persistence.run_store.get_run_store", return_value=store):
            result = runner.invoke(report_cmd, ["--list"])
        assert result.exit_code == 0
        assert "run-0" in result.output
        assert "run-1" in result.output

    def test_list_json(self):
        from cherenkov.cli.commands.report import report_cmd
        records = [_make_record(run_id="run-x", grade="A", verdict="CERTIFIED")]
        store = _mock_store(records)
        runner = CliRunner()
        with patch("cherenkov.persistence.run_store.get_run_store", return_value=store):
            result = runner.invoke(report_cmd, ["--list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["run_id"] == "run-x"
        assert data[0]["grade"] == "A"

    def test_list_markdown(self):
        from cherenkov.cli.commands.report import report_cmd
        records = [_make_record(run_id="run-md")]
        store = _mock_store(records)
        runner = CliRunner()
        with patch("cherenkov.persistence.run_store.get_run_store", return_value=store):
            result = runner.invoke(report_cmd, ["--list", "--format", "markdown"])
        assert result.exit_code == 0
        assert "# Run History" in result.output
        assert "run-md" in result.output

    def test_list_empty_store(self):
        from cherenkov.cli.commands.report import report_cmd
        store = _mock_store([])
        runner = CliRunner()
        with patch("cherenkov.persistence.run_store.get_run_store", return_value=store):
            result = runner.invoke(report_cmd, ["--list"])
        assert result.exit_code == 0
        assert "No runs found" in result.output

    def test_diff_run_ids_text(self):
        from cherenkov.cli.commands.report import report_cmd
        rec_a = _make_record(run_id="run-a", grade="B", verdict="SUSPECT")
        rec_b = _make_record(run_id="run-b", grade="A", verdict="CERTIFIED")
        diff_result = {
            "run_a": "run-a", "run_b": "run-b",
            "divergence_delta": -2,
            "verdict_changed": True,
            "verdict_a": "SUSPECT", "verdict_b": "CERTIFIED",
            "coverage_delta": 5.0,
            "timestamp_a": rec_a.timestamp,
            "timestamp_b": rec_b.timestamp,
        }
        store = _mock_store([rec_a, rec_b], diff_result=diff_result)
        runner = CliRunner()
        with patch("cherenkov.cli.commands.report._resolve_run", return_value=rec_b), \
             patch("cherenkov.persistence.run_store.get_run_store", return_value=store):
            result = runner.invoke(report_cmd, ["--run", "run-b", "--diff", "run-a"])
        assert result.exit_code == 0
        assert "SUSPECT" in result.output
        assert "CERTIFIED" in result.output
        assert "↑" in result.output  # grade improved B→A

    def test_diff_run_ids_json(self):
        from cherenkov.cli.commands.report import report_cmd
        rec_a = _make_record(run_id="run-a", grade="C")
        rec_b = _make_record(run_id="run-b", grade="B")
        diff_result = {
            "run_a": "run-a", "run_b": "run-b",
            "divergence_delta": -1,
            "verdict_changed": False,
            "verdict_a": "SUSPECT", "verdict_b": "SUSPECT",
            "coverage_delta": 2.0,
            "timestamp_a": "2026-06-28T10:00:00Z",
            "timestamp_b": "2026-06-29T10:00:00Z",
        }
        store = _mock_store([rec_a, rec_b], diff_result=diff_result)
        runner = CliRunner()
        with patch("cherenkov.cli.commands.report._resolve_run", return_value=rec_b), \
             patch("cherenkov.persistence.run_store.get_run_store", return_value=store):
            result = runner.invoke(report_cmd, ["--run", "run-b", "--diff", "run-a", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["grade_a"] == "C"
        assert data["grade_b"] == "B"
        assert data["grade_delta"] == 1  # B(4) - C(3) = 1

    def test_fail_on_new_with_positive_divergence_delta(self):
        from cherenkov.cli.commands.report import report_cmd
        rec_a = _make_record(run_id="run-a")
        rec_b = _make_record(run_id="run-b")
        diff_result = {
            "run_a": "run-a", "run_b": "run-b",
            "divergence_delta": 3,
            "verdict_changed": True,
            "verdict_a": "CERTIFIED", "verdict_b": "SUSPECT",
            "coverage_delta": None,
            "timestamp_a": rec_a.timestamp,
            "timestamp_b": rec_b.timestamp,
        }
        store = _mock_store([rec_a, rec_b], diff_result=diff_result)
        runner = CliRunner()
        with patch("cherenkov.cli.commands.report._resolve_run", return_value=rec_b), \
             patch("cherenkov.persistence.run_store.get_run_store", return_value=store):
            result = runner.invoke(report_cmd, ["--run", "run-b", "--diff", "run-a", "--fail-on-new"])
        assert result.exit_code == 1

    def test_fail_on_new_with_negative_delta_exits_0(self):
        from cherenkov.cli.commands.report import report_cmd
        rec_a = _make_record(run_id="run-a")
        rec_b = _make_record(run_id="run-b")
        diff_result = {
            "run_a": "run-a", "run_b": "run-b",
            "divergence_delta": -1,
            "verdict_changed": False,
            "verdict_a": "CERTIFIED", "verdict_b": "CERTIFIED",
            "coverage_delta": None,
            "timestamp_a": rec_a.timestamp,
            "timestamp_b": rec_b.timestamp,
        }
        store = _mock_store([rec_a, rec_b], diff_result=diff_result)
        runner = CliRunner()
        with patch("cherenkov.cli.commands.report._resolve_run", return_value=rec_b), \
             patch("cherenkov.persistence.run_store.get_run_store", return_value=store):
            result = runner.invoke(report_cmd, ["--run", "run-b", "--diff", "run-a", "--fail-on-new"])
        assert result.exit_code == 0
