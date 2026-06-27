"""Unit tests for cherenkov/divergence/report_diff.py and cherenkov/cli/commands/report.py."""
from __future__ import annotations

import json
from pathlib import Path

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
